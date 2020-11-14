import asyncio

import pytest
import websockets

from test_fixtures import root_uri, make_root

#
# Tests
#

pytestmark = pytest.mark.asyncio

async def test_Location_without_plugin_returns_500(root_uri):
    uri = root_uri + "/bad-config"

    with pytest.raises(websockets.exceptions.InvalidStatusCode) as excinfo:
        async with websockets.connect(uri):
            pass

    assert excinfo.value.status_code == 500

async def test_mismatched_Origins_are_allowed_with_OriginCheck_Off(root_uri):
    uri = root_uri + "/no-origin-check"
    origin = 'http://not-my-origin.com'

    async with websockets.connect(uri, extra_headers=[('Origin', origin)]):
        pass # should succeed

# Matches the Trusted list for /origin-trusted in httpd/test.conf.
TRUSTED_ORIGINS = [
    'http://origin-one',
    'https://origin-two:55',
    'https://origin-three',
]

@pytest.mark.parametrize("origin", TRUSTED_ORIGINS)
async def test_explicitly_trusted_Origins_are_allowed(root_uri, origin):
    uri = root_uri + "/origin-trusted"

    async with websockets.connect(uri, extra_headers=[('Origin', origin)]):
        pass # should succeed

async def test_untrusted_Origins_are_not_allowed_with_OriginCheck_Trusted(root_uri):
    # When using WebSocketOriginCheck Trusted, even a same-origin request isn't
    # good enough if the origin is not on the allowlist.
    uri = root_uri + "/origin-trusted"
    origin = make_root()

    with pytest.raises(websockets.exceptions.InvalidStatusCode) as excinfo:
        async with websockets.connect(uri, extra_headers=[('Origin', origin)]):
            pass

    assert excinfo.value.status_code == 403
