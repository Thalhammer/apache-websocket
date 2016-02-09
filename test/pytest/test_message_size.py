import autobahn.twisted.websocket as ws
import pytest
import struct

from twisted.internet import defer

from testutil.websocket import make_root, SCHEME

CLOSE_CODE_NORMAL_CLOSURE  = 1000
CLOSE_CODE_MESSAGE_TOO_BIG = 1009

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT         = 0x1

ROOT = make_root("wss" if (SCHEME == "https") else "ws")

#
# Autobahn Subclasses
#

class MessageTestProtocol(ws.WebSocketClientProtocol):
    """
    Implements WebSocketClientProtocol for the message tests.

    The opened and closed attributes are Deferreds that can be waited on. The
    closed Deferred will return the received close code in its callback.
    """
    def __init__(self):
        ws.WebSocketClientProtocol.__init__(self)

        self.opened = defer.Deferred()
        self.closed = defer.Deferred()

    def onOpen(self):
        self.opened.callback(None)

    def onClose(self, wasClean, code, reason):
        assert wasClean
        self.closed.callback(code)

class MessageTestFactory(ws.WebSocketClientFactory):
    """
    An implementation of WebSocketClientFactory that allows its client code to
    retrieve the first protocol instance that is built using the connected
    callback.
    """
    protocol = MessageTestProtocol

    def __init__(self, uri):
        ws.WebSocketClientFactory.__init__(self, uri)
        self.proto = None
        self.connected = defer.Deferred()

    def buildProtocol(self, addr):
        proto = MessageTestProtocol()
        proto.factory = self

        self.connected.callback(proto)
        return proto

#
# Fixtures
#

def connect(uri):
    """
    Constructs a MessageTestFactory, connects to the desired WebSocket endpoint
    URI, waits for the MessageTestProtocol to be constructed, and then returns
    the protocol instance.
    """
    factory = MessageTestFactory(uri)
    factory.setProtocolOptions(failByDrop=False, openHandshakeTimeout=1)

    ws.connectWS(factory, timeout=1)
    protocol = pytest.blockon(factory.connected)

    pytest.blockon(protocol.opened)
    return protocol

@pytest.fixture
def proto():
    """
    A fixture that returns a WebSocket protocol connection to an endpoint with a
    MaxMessageSize of 4.
    """
    return connect(ROOT + "/size-limit")

#
# Tests
#

@pytest.inlineCallbacks
def test_overlarge_single_messages_are_rejected_when_using_MaxMessageSize(proto):
    proto.sendMessage('12345')
    response = yield proto.closed
    assert response == CLOSE_CODE_MESSAGE_TOO_BIG

@pytest.inlineCallbacks
def test_overlarge_fragmented_messages_are_rejected_when_using_MaxMessageSize(proto):
    proto.sendFrame(opcode=OPCODE_TEXT, payload='x', fin=False)

    for _ in range(4):
        proto.sendFrame(opcode=OPCODE_CONTINUATION, payload='x', fin=False)

    response = yield proto.closed
    assert response == CLOSE_CODE_MESSAGE_TOO_BIG

@pytest.inlineCallbacks
def test_overlarge_fragmented_messages_are_still_rejected_with_interleaved_control_frames(proto):
    proto.sendFrame(opcode=OPCODE_TEXT, payload='x', fin=False)
    proto.sendPing() # send a control frame to split up the text message

    for _ in range(4):
        proto.sendFrame(opcode=OPCODE_CONTINUATION, payload='x', fin=False)

    response = yield proto.closed
    assert response == CLOSE_CODE_MESSAGE_TOO_BIG

@pytest.inlineCallbacks
def test_overflowing_fragmented_messages_are_rejected_when_using_MaxMessageSize(proto):
    # For a signed 64-bit internal implementation, a fragment of one byte plus a
    # fragment of (2^63 - 1) bytes will overflow into a negative size. The
    # server needs to deal with this case gracefully.
    proto.sendFrame(opcode=OPCODE_TEXT, payload='x', fin=False)

    # Unfortunately we can't call sendFrame() with our desired length, because
    # it'll actually attempt to buffer a payload in memory and die. Manually
    # construct a (partial) frame ourselves.
    frame = b''.join([
        b'\x80', # FIN bit set, no RSVx bits, opcode 0 (continuation)
        b'\xFF', # MASK bit set, length of "127" (the 8-byte flag value)
        struct.pack("!Q", 0x7FFFFFFFFFFFFFFFL) # largest possible length

        # We don't need the rest of the frame header; the server should reject
        # it at this point.
    ])
    proto.sendData(frame)

    response = yield proto.closed
    assert response == CLOSE_CODE_MESSAGE_TOO_BIG

@pytest.inlineCallbacks
def test_several_messages_under_the_MaxMessageSize_are_allowed(proto):
    proto.sendMessage('1234')
    proto.sendMessage('1234')
    proto.sendMessage('1234')
    proto.sendMessage('1234')

    proto.sendClose(CLOSE_CODE_NORMAL_CLOSURE)
    response = yield proto.closed
    assert response == CLOSE_CODE_NORMAL_CLOSURE

@pytest.inlineCallbacks
def test_control_frames_are_also_affected_by_MaxMessageSize(proto):
    # Two-byte close code, three-byte payload: five bytes total
    proto.sendClose(CLOSE_CODE_NORMAL_CLOSURE, "123")

    response = yield proto.closed
    assert response == CLOSE_CODE_MESSAGE_TOO_BIG

@pytest.inlineCallbacks
def test_several_control_frames_under_the_MaxMessageSize_are_allowed(proto):
    proto.sendPing('1234')
    proto.sendPing('1234')
    proto.sendPing('1234')
    proto.sendPing('1234')

    proto.sendClose(CLOSE_CODE_NORMAL_CLOSURE)
    response = yield proto.closed
    assert response == CLOSE_CODE_NORMAL_CLOSURE
