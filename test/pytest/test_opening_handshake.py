import asyncio
import re

import aiohttp
import pytest
import websockets

from test_fixtures import root_uri, make_authority, make_root
from test_fixtures import HOST, HOST_IPV6, SCHEME

pytestmark = pytest.mark.asyncio

#
# Helpers
#

# from `openssl rand -base64 16`. guaranteed to be random.
UPGRADE_KEY = '36zg57EA+cDLixMBxrDj4g=='

# base64(SHA1(UPGRADE_KEY:"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))
UPGRADE_ACCEPT = 'eGic2At3BJQkGyA4Dq+3nczxEJo='

def assert_successful_upgrade(response):
    """
    Asserts that a server's response to a WebSocket Upgrade request is correct
    and successful.
    """
    # The server must upgrade with a 101 response.
    assert response.status == 101

    # We need to see Connection: Upgrade and Upgrade: websocket.
    connection = response.headers.getall("Connection")
    assert "upgrade" in [h.lower() for h in connection]

    upgrade = response.headers.getall("Upgrade")
    assert len(upgrade) == 1
    assert upgrade[0].lower() == "websocket"

    # The Sec-WebSocket-Accept header should match our precomputed digest.
    accept = response.headers.getall("Sec-WebSocket-Accept")
    assert len(accept) == 1
    assert accept[0] == UPGRADE_ACCEPT

def assert_headers_match(actual_headers, expected_list):
    """
    Asserts that the header values in the given list match the expected list of
    values. Headers will be split on commas.
    """
    # This regex matches all "OWS , OWS" separators in a header value.
    sep_ex = re.compile(r"[ \t]*,[ \t]*")

    actual_list = []
    if actual_headers is None:
        actual_headers = []

    for header in actual_headers:
        # Collapse list whitespace, then split on commas to get the list of
        # values.
        values = sep_ex.sub(',', header).split(',')
        actual_list.extend(values)

    assert actual_list == expected_list

def websocket_headers(*, key=UPGRADE_KEY, version=None, protocol=None,
                      origin=None, host=None, connection=None):
    if version is None:
        version = '13'

    if connection is None:
        connection = "Upgrade"

    hdrs = {
        "Upgrade": "websocket",
        "Connection": connection,
        "Sec-WebSocket-Key": key,
        "Sec-WebSocket-Version": version,
    }

    if protocol is not None:
        hdrs["Sec-WebSocket-Protocol"] = protocol

    if origin is not None:
        if int(version) < 8:
            hdrs["Sec-WebSocket-Origin"] = origin
        else:
            hdrs["Origin"] = origin

    if host is not None:
        hdrs["Host"] = host

    return hdrs

# Supported WebSocket implementation versions, ordered by preference.
SUPPORTED_VERSIONS = [ '13', '8', '7' ]

#
# Fixtures
#

@pytest.fixture(scope='module')
def event_loop():
    """Redefines the standard pytest-asyncio event loop to have module scope."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope='module')
async def http():
    """
    A fixture that returns an aiohttp client session. A single session is cached
    and reused for all tests in this module.
    """
    async with aiohttp.ClientSession() as client:
        yield client

@pytest.fixture
def uri():
    """
    Every test in this file uses the same uri.
    """
    return make_root() + "/echo"

#
# Tests
#

@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
@pytest.mark.parametrize("connection", [
    "Upgrade",
    "Upgrade, close",
    "close, Upgrade,",
])
async def test_valid_handshake_is_upgraded_correctly(http, uri, version, connection):
    headers = websocket_headers(version=version, connection=connection)

    async with http.get(uri, headers=headers) as resp:
        assert_successful_upgrade(resp)

@pytest.mark.parametrize("method", [ 'POST', 'PUT', 'DELETE', 'HEAD' ])
async def test_handshake_is_refused_if_method_is_not_GET(http, uri, method):
    headers = websocket_headers()

    async with http.request(method, uri, headers=headers) as resp:
        assert 400 <= resp.status < 500

@pytest.mark.parametrize("bad_version", [
    '',
    'abcdef',
    '+13',
    '13sdfj',
    '1300',
    '013',
    '-1',
    '256',
    '8_',
])
async def test_handshake_is_refused_for_invalid_version(http, uri, bad_version):
    headers = websocket_headers(version=bad_version)

    async with http.get(uri, headers=headers) as resp:
        assert resp.status == 400

@pytest.mark.parametrize("bad_version", ['0', '9', '14', '255'])
async def test_handshake_is_refused_for_unsupported_versions(http, uri, bad_version):
    headers = websocket_headers(version=bad_version)

    async with http.get(uri, headers=headers) as resp:
        assert resp.status == 400

        # Make sure the server advertises its supported versions, as well.
        versions = resp.headers.getall("Sec-WebSocket-Version")
        assert_headers_match(versions, SUPPORTED_VERSIONS)

@pytest.mark.parametrize("bad_key", [
    "toosmall",
    "wayyyyyyyyyyyyyyyyyyyytoobig",
    "invalid!characters_89A==",
    "badlastcharacterinkey+==",
    "WRONGPADDINGLENGTH012A?=",
    "JUNKATENDOFPADDING456A=?",
])
async def test_handshake_is_refused_for_bad_key(http, uri, bad_key):
    headers = websocket_headers(key=bad_key)

    async with http.get(uri, headers=headers) as resp:
        assert resp.status == 400

@pytest.mark.parametrize("bad_protocol", [
    "",
    " ",
    "\t",
    ",",
    ",,",
    "bad token",
    "\"token\"",
    "bad/token",
    "bad\\token",
    "valid, invalid{}",
    "bad; separator",
    "control\x05character",
    "bad\ttoken",
])
async def test_handshake_is_refused_for_bad_subprotocols(http, uri, bad_protocol):
    headers = websocket_headers(protocol=bad_protocol)

    async with http.get(uri, headers=headers) as resp:
        assert resp.status == 400

async def test_HTTP_10_handshakes_are_refused(uri):
    headers = websocket_headers()

    async with aiohttp.request('GET', uri, headers=headers,
                               version=aiohttp.HttpVersion10) as resp:
        assert 400 <= resp.status < 500

@pytest.mark.parametrize(("host", "version"), [
    (HOST, '13'),
    (HOST_IPV6, '13'),
    (HOST, '8'),
    (HOST, '7'),
])
async def test_same_Origin_is_allowed(http, uri, host, version):
    authority = make_authority(host=host)
    origin = make_root(host=host)

    headers = websocket_headers(origin=origin, host=authority, version=version)

    async with http.get(uri, headers=headers) as resp:
        assert_successful_upgrade(resp)

OPPOSITE_SCHEME = 'https' if (SCHEME == 'http') else 'http'

@pytest.mark.parametrize(("origin", "host", "version"), [
    ("http://not-my-origin.com", None, None),
    ("http://not-my-origin.com", None, '7'),
    ("http://not-my-origin.com", None, '8'),
    (make_root(port=55), None, None),
    (OPPOSITE_SCHEME + "://" + make_authority(), None, None),
    (make_root(), make_authority(port=55), None),
])
async def test_mismatched_Origins_are_refused(http, uri, origin, host, version):
    headers = websocket_headers(origin=origin, host=host, version=version)

    async with http.get(uri, headers=headers) as resp:
        assert resp.status == 403
