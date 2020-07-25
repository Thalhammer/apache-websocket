import asyncio

import pytest
import websockets
import websockets.framing

from test_fixtures import root_uri

CLOSE_CODE_PROTOCOL_ERROR = 1002

#
# Fixtures
#

@pytest.fixture
def permit_illegal_close(monkeypatch):
    """
    This fixture provides a function that monkeypatches the websockets library
    to allow an illegal outgoing close code.
    """
    def f(code):
        allowed = websockets.framing.EXTERNAL_CLOSE_CODES + [code]
        monkeypatch.setattr(websockets.framing, "EXTERNAL_CLOSE_CODES", allowed)
    return f

@pytest.fixture
async def default_conn(root_uri):
    """A fixture that returns a WebSocket protocol connection to an endpoint
    that has no WebSocketAllowReservedStatusCodes directive."""
    uri = root_uri + "/echo"
    async with websockets.connect(uri) as conn:
        yield conn

@pytest.fixture
async def allow_conn(root_uri):
    """A fixture that returns a WebSocket protocol connection to an endpoint
    that has WebSocketAllowReservedStatusCodes enabled."""
    uri = root_uri + "/echo-allow-reserved"
    async with websockets.connect(uri) as conn:
        yield conn

#
# Tests
#

pytestmark = pytest.mark.asyncio

async def test_1000_is_always_allowed(allow_conn):
    await allow_conn.close(1000)
    assert allow_conn.close_code != CLOSE_CODE_PROTOCOL_ERROR

NEVER_ALLOWED = [
    1005,
    1006,
    1015,
]

@pytest.mark.parametrize("code", NEVER_ALLOWED)
async def test_some_close_codes_are_always_forbidden(allow_conn, permit_illegal_close, code):
    permit_illegal_close(code)

    await allow_conn.close(code)
    assert allow_conn.close_code == CLOSE_CODE_PROTOCOL_ERROR

ALLOWED_WITH_CONFIG = [
    1004, # "reserved"
    1014, # bad gateway. TODO this should now be allowed by default
    1016, # beginning of unassigned block as of July 2020
    2000,
    2999, # end of reserved-for-specification block
]

@pytest.mark.parametrize("code", ALLOWED_WITH_CONFIG)
async def test_reserved_close_codes_are_rejected_by_default(default_conn, permit_illegal_close, code):
    permit_illegal_close(code)

    await default_conn.close(code)
    assert default_conn.close_code == CLOSE_CODE_PROTOCOL_ERROR

@pytest.mark.parametrize("code", ALLOWED_WITH_CONFIG)
async def test_reserved_close_codes_are_allowed_via_configuration(allow_conn, permit_illegal_close, code):
    permit_illegal_close(code)

    await allow_conn.close(code)
    assert allow_conn.close_code != CLOSE_CODE_PROTOCOL_ERROR
