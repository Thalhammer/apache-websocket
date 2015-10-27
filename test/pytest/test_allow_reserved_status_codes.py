import autobahn.twisted.websocket as ws
import pytest

from twisted.internet import defer

CLOSE_CODE_PROTOCOL_ERROR = 1002

#
# Autobahn Subclasses
#

class CloseTestProtocol(ws.WebSocketClientProtocol):
    """
    Implements WebSocketClientProtocol for the close tests.

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

    # XXX Monkey-patch sendClose() to allow invalid codes on the wire.
    def sendClose(self, code=None, reason=None):
        self.sendCloseFrame(code=code, isReply=False)

class CloseTestFactory(ws.WebSocketClientFactory):
    """
    An implementation of WebSocketClientFactory that allows the its client code
    to retrieve the first protocol instance that is built using the connected
    callback.
    """
    protocol = CloseTestProtocol

    def __init__(self, uri):
        ws.WebSocketClientFactory.__init__(self, uri)
        self.proto = None
        self.connected = defer.Deferred()

    def buildProtocol(self, addr):
        proto = CloseTestProtocol()
        proto.factory = self

        self.connected.callback(proto)
        return proto

#
# Helpers
#

def succeeded(code):
    return code != CLOSE_CODE_PROTOCOL_ERROR

def failed(code):
    return not succeeded(code)

#
# Fixtures
#

def connect(uri):
    """
    Constructs a CloseTestFactory, connects to the desired WebSocket endpoint
    URI, waits for the CloseTestProtocol to be constructed, and then returns the
    protocol instance.
    """
    factory = CloseTestFactory(uri)
    factory.setProtocolOptions(failByDrop=False, openHandshakeTimeout=1)

    ws.connectWS(factory, timeout=1)
    protocol = pytest.blockon(factory.connected)

    pytest.blockon(protocol.opened)
    return protocol

@pytest.fixture
def default_proto():
    """A fixture that returns a WebSocket protocol connection to an endpoint
    that has no WebSocketAllowReservedStatusCodes directive."""
    return connect("ws://127.0.0.1/echo")

@pytest.fixture
def allow_proto():
    """A fixture that returns a WebSocket protocol connection to an endpoint
    that has WebSocketAllowReservedStatusCodes enabled."""
    return connect("ws://127.0.0.1/echo-allow-reserved")

#
# Tests
#

@pytest.inlineCallbacks
def test_1000_is_always_allowed(allow_proto):
    allow_proto.sendClose(1000)
    response = yield allow_proto.closed
    assert succeeded(response)

@pytest.inlineCallbacks
def test_1004_is_rejected_by_default(default_proto):
    default_proto.sendClose(1004)
    response = yield default_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_1004_is_allowed_when_allowing_reserved(allow_proto):
    allow_proto.sendClose(1004)
    response = yield allow_proto.closed
    assert succeeded(response)

@pytest.inlineCallbacks
def test_1005_is_never_allowed(allow_proto):
    allow_proto.sendClose(1005)
    response = yield allow_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_1006_is_never_allowed(allow_proto):
    allow_proto.sendClose(1006)
    response = yield allow_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_1014_is_rejected_by_default(default_proto):
    default_proto.sendClose(1014)
    response = yield default_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_1014_is_allowed_when_allowing_reserved(allow_proto):
    allow_proto.sendClose(1014)
    response = yield allow_proto.closed
    assert succeeded(response)

@pytest.inlineCallbacks
def test_1015_is_never_allowed(allow_proto):
    allow_proto.sendClose(1015)
    response = yield allow_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_1016_is_rejected_by_default(default_proto):
    default_proto.sendClose(1016)
    response = yield default_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_1016_is_allowed_when_allowing_reserved(allow_proto):
    allow_proto.sendClose(1016)
    response = yield allow_proto.closed
    assert succeeded(response)

@pytest.inlineCallbacks
def test_2000_is_rejected_by_default(default_proto):
    default_proto.sendClose(2000)
    response = yield default_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_2000_is_allowed_when_allowing_reserved(allow_proto):
    allow_proto.sendClose(2000)
    response = yield allow_proto.closed
    assert succeeded(response)

@pytest.inlineCallbacks
def test_2999_is_rejected_by_default(default_proto):
    default_proto.sendClose(2999)
    response = yield default_proto.closed
    assert failed(response)

@pytest.inlineCallbacks
def test_2999_is_allowed_when_allowing_reserved(allow_proto):
    allow_proto.sendClose(2999)
    response = yield allow_proto.closed
    assert succeeded(response)
