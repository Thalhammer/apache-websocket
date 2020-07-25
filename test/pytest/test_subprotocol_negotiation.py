import asyncio

import pytest
import websockets

from test_fixtures import root_uri

pytestmark = pytest.mark.asyncio

async def test_no_subprotocol_is_negotiated_by_default(root_uri):
    uri = root_uri + "/echo"
    subprotocols = ["my_protocol"]

    async with websockets.connect(uri, subprotocols=subprotocols) as conn:
        assert conn.subprotocol == None

@pytest.mark.parametrize("protocol_header", [
    # All of the following Sec-WebSocket-Protocol header values are valid.
    "dumb-increment-protocol",
    "   dumb-increment-protocol  ,",
    "\tdumb-increment-protocol\t",
    "echo, dumb-increment-protocol",
    "dumb-increment-protocol, echo",
    ", , dumb-increment-protocol, ",
])
async def test_negotiation_of_known_subprotocol_succeeds(root_uri, protocol_header):
    uri = root_uri + "/dumb-increment"

    # XXX We must set the subprotocols list in addition to the
    # Sec-WebSocket-Protocol header so that the websockets library doesn't treat
    # the returned subprotocol as unexpected. We're abusing the API here; hence
    # the added complication.
    expected = "dumb-increment-protocol"
    subprotocols = [expected]
    headers = { 'Sec-WebSocket-Protocol': protocol_header }

    async with websockets.connect(uri,
                                  subprotocols=subprotocols,
                                  extra_headers=headers) as conn:
        assert conn.subprotocol == expected
