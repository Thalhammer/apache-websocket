import pytest

from twisted.web import client

from testutil.fixtures import agent
from testutil.websocket import assert_successful_upgrade, make_request, \
                               make_root

#
# Fixtures
#

@pytest.yield_fixture(params=['http://origin-one', 'https://origin-two:55',
                              'https://origin-three'])
def trusted_origin_response(agent, request):
    """
    A fixture that performs a handshake using one of the explicitly trusted test
    Origins.
    """
    response = pytest.blockon(make_request(agent, path='/origin-trusted',
                                                  origin=request.param))
    yield response
    client.readBody(response).cancel() # immediately close the connection

#
# Tests
#

@pytest.inlineCallbacks
def test_Location_without_plugin_returns_500(agent):
    response = yield make_request(agent, path='/bad-config')
    assert response.code == 500
    client.readBody(response).cancel() # immediately close the connection

@pytest.inlineCallbacks
def test_mismatched_Origins_are_allowed_with_OriginCheck_Off(agent):
    response = yield make_request(agent, path='/no-origin-check',
                                  origin='http://not-my-origin.com')
    assert_successful_upgrade(response)
    client.readBody(response).cancel() # immediately close the connection

def test_explicitly_trusted_Origins_are_allowed(trusted_origin_response):
    assert_successful_upgrade(trusted_origin_response)

@pytest.inlineCallbacks
def test_untrusted_Origins_are_not_allowed_with_OriginCheck_Trusted(agent):
    # When using WebSocketOriginCheck Trusted, even a same-origin request isn't
    # good enough if the origin is not on the allowlist.
    response = yield make_request(agent, path='/origin-trusted',
                                  origin=make_root())
    assert response.code == 403
    client.readBody(response).cancel() # immediately close the connection
