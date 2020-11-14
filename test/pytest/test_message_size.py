import asyncio
import struct

import pytest
import websockets

from test_fixtures import root_uri

CLOSE_CODE_NORMAL_CLOSURE  = 1000
CLOSE_CODE_MESSAGE_TOO_BIG = 1009

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT         = 0x1

pytestmark = pytest.mark.asyncio

#
# Helpers
#

class WebSocketDebugProtocol(websockets.client.WebSocketClientProtocol):
    """
    A WebSocketClientProtocol that additionally allows arbitrary data to be
    written to the transport.

    XXX This class uses internal APIs that aren't guaranteed to remain stable.
    """
    def direct_write(self, data: bytes):
        self.transport.write(data)

        # To be truly correct, we'd handle flow control here, but for the
        # purposes of these tests, it probably doesn't much matter. The APIs for
        # doing so are internal anyway, and coupling against them would be
        # fragile.

class StopWriting(Exception):
    """An exception to interrupt the writing of a fragmented message."""
    pass

#
# Fixtures
#

@pytest.fixture
async def conn(root_uri):
    """
    A fixture that returns a WebSocketDebugProtocol connection to an endpoint
    with a MaxMessageSize of 4.
    """
    uri = root_uri + "/size-limit"

    async with websockets.connect(uri, create_protocol=WebSocketDebugProtocol) as conn:
        yield conn

#
# Tests
#

async def test_overlarge_single_messages_are_rejected_when_using_MaxMessageSize(conn):
    await conn.send('12345')

    await asyncio.wait_for(conn.wait_closed(), timeout=1.0)
    assert conn.close_code == CLOSE_CODE_MESSAGE_TOO_BIG

async def test_overlarge_fragmented_messages_are_rejected_when_using_MaxMessageSize(conn):
    async def fragmented_message(size):
        for _ in range(size):
            yield 'x'

    await conn.send(fragmented_message(5))

    await asyncio.wait_for(conn.wait_closed(), timeout=1.0)
    assert conn.close_code == CLOSE_CODE_MESSAGE_TOO_BIG

async def test_overlarge_fragmented_messages_are_still_rejected_with_interleaved_control_frames(conn):
    async def fragmented_message_with_ping(size):
        yield 'x'

        # send a control frame to split up the text message
        pong = await conn.ping()
        await pong

        for _ in range(size-1):
            yield 'x'

    await conn.send(fragmented_message_with_ping(5))

    await asyncio.wait_for(conn.wait_closed(), timeout=1.0)
    assert conn.close_code == CLOSE_CODE_MESSAGE_TOO_BIG

async def test_overflowing_fragmented_messages_are_rejected_when_using_MaxMessageSize(conn):
    # For a signed 64-bit internal implementation, a fragment of one byte plus a
    # fragment of (2^63 - 1) bytes will overflow into a negative size. The
    # server needs to deal with this case gracefully.
    async def gigantic_fragmented_message():
        yield 'x' # send one byte first

        # Unfortunately we can't call send() with our desired length, because
        # we'd have to buffer all that data in memory. Manually construct a
        # (partial) frame ourselves, and send it via the WebSocketDebugProtocol.
        frame = b''.join([
            b'\x80', # FIN bit set, no RSVx bits, opcode 0 (continuation)
            b'\xFF', # MASK bit set, length of "127" (the 8-byte flag value)
            struct.pack("!Q", 0x7FFFFFFFFFFFFFFF) # largest possible length

            # We don't need the rest of the frame header; the server should
            # reject it at this point.
        ])

        # The server should immediately close the connection after receiving the
        # partial header. NOTE: we perform the wait here, rather than outside
        # the message generator, because otherwise the websockets package will
        # send its own close code when we interrupt the message with the
        # StopWriting exception.
        conn.direct_write(frame)
        await asyncio.wait_for(conn.wait_closed(), timeout=1.0)

        # XXX The websockets package doesn't deal with the server closing the
        # connection mid-message particularly gracefully; it tries to keep
        # writing fragments anyway and raises InvalidState rather than
        # ConnectionClosed. Interrupt the message writing with our own
        # exception.
        raise StopWriting()

    with pytest.raises(StopWriting):
        await conn.send(gigantic_fragmented_message())

    assert conn.close_code == CLOSE_CODE_MESSAGE_TOO_BIG

async def test_several_messages_under_the_MaxMessageSize_are_allowed(conn):
    await conn.send('1234')
    await conn.send('1234')
    await conn.send('1234')
    await conn.send('1234')

    await conn.close()
    assert conn.close_code == CLOSE_CODE_NORMAL_CLOSURE

async def test_control_frames_are_also_affected_by_MaxMessageSize(conn):
    # Two-byte close code, three-byte payload: five bytes total
    await conn.close(CLOSE_CODE_NORMAL_CLOSURE, "123")
    assert conn.close_code == CLOSE_CODE_MESSAGE_TOO_BIG

async def test_several_control_frames_under_the_MaxMessageSize_are_allowed(conn):
    await conn.ping('1234')
    await conn.ping('2345')
    await conn.ping('3456')
    await conn.ping('4567')

    await conn.close()
    assert conn.close_code == CLOSE_CODE_NORMAL_CLOSURE
