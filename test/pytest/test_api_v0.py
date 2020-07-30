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
