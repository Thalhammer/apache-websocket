import asyncio
import json

import pytest
import websockets

from test_fixtures import root_uri

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
            await conn.send(f"header: {h}")
            resp = await asyncio.wait_for(conn.recv(), timeout=1.0)

            assert resp == headers[h]

async def test_plugin_get_header_returns_null_for_nonexistent_headers(uri):
    async with websockets.connect(uri) as conn:
        await conn.send("header: X-Does-Not-Exist")
        resp = await asyncio.wait_for(conn.recv(), timeout=1.0)

    assert resp == '<null>'
