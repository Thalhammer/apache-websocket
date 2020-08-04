import asyncio
import json

import pytest
import websockets

from test_fixtures import root_uri

#
# Helpers
#

async def rpc(conn, msg):
    """Sends a text message and waits one second for a response."""
    await conn.send(msg)
    return await asyncio.wait_for(conn.recv(), timeout=1.0)

#
# Fixtures
#

@pytest.fixture
def uri(root_uri):
    return root_uri + '/debug/v0'

#
# Tests
#

pytestmark = pytest.mark.asyncio

async def test_plugin_close_sends_no_status_code(uri):
    async with websockets.connect(uri) as conn:
        await conn.send("close")
        await asyncio.wait_for(conn.wait_closed(), timeout=1.0)

    assert conn.close_code == 1005

async def test_plugin_get_header_retrieves_request_headers(uri):
    headers = {
        'X-Debug-0': 'some value',
        'X-Debug-1': 'some other value',
    }

    async with websockets.connect(uri, extra_headers=headers) as conn:
        for h in headers:
            resp = await rpc(conn, f"header: {h}")
            assert resp == headers[h]

async def test_plugin_get_header_returns_null_for_nonexistent_headers(uri):
    async with websockets.connect(uri) as conn:
        resp = await rpc(conn, "header: X-Does-Not-Exist")

    assert resp == '<null>'

async def test_plugin_set_header_sets_response_header(uri):
    async with websockets.connect(uri) as conn:
        assert conn.response_headers["X-Debug-Header"] == "true"

async def test_server_version_is_passed_to_plugin(uri):
    async with websockets.connect(uri) as conn:
        resp = await rpc(conn, "version")

    assert resp == "1"

async def test_plugin_can_get_and_set_subprotocols(uri):
    subprotocols = [ "a", "b", "c" ]

    for i in range(len(subprotocols)):
        headers = { "X-Choose-Subprotocol": i }

        async with websockets.connect(uri, subprotocols=subprotocols,
                                      extra_headers=headers) as conn:
            assert conn.subprotocol == subprotocols[i]

@pytest.mark.parametrize("subprotocols", [
    None,
    [ "a", "b", "c" ],
])
async def test_protocol_count_is_set_to_length_of_subprotocols_list(uri, subprotocols):
    subprotocol_num = 0
    if subprotocols is not None:
        subprotocol_num = len(subprotocols)

    async with websockets.connect(uri, subprotocols=subprotocols) as conn:
        assert conn.subprotocol is None

        resp = await rpc(conn, "proto-count")
        assert resp == str(subprotocol_num)

async def test_plugin_on_connect_may_refuse_connections(uri):
    headers = { "X-Refuse-Connection": "1" }

    with pytest.raises(websockets.exceptions.InvalidStatusCode) as excinfo:
        async with websockets.connect(uri, extra_headers=headers) as conn:
            pass

    assert excinfo.value.status_code == 403

async def test_plugin_send_is_correctly_mutexed(root_uri):
    uri = root_uri + "/threads"
    counts = {}

    async with websockets.connect(uri) as conn:
        async for msg in conn:
            index, count = msg.split(': ', 1)

            if index not in counts:
                assert count == '1000'
            else:
                previous = int(counts[index])
                assert count == str(previous - 1)

            counts[index] = count

    for index in counts:
        assert counts[index] == '1'
