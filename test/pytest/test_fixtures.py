import pytest

#
# Helpers
#

# TODO: make these configurable
HOST = '127.0.0.1'
HOST_IPV6 = '[::1]'

SCHEME = "http"
PORT = 59153

def make_authority(scheme=SCHEME, host=HOST, port=PORT):
    """Returns host[:port] for use in a Host header."""
    is_default_port = ((scheme in ["http", "ws"] and port == 80) or
                       (scheme in ["https", "wss"] and port == 443))
    root = host

    if not is_default_port:
        root += ":{0}".format(port)

    return root

def make_root(scheme=SCHEME, host=HOST, port=PORT):
    """Returns scheme://host[:port] to create a root URL for testing."""
    return scheme + "://" + make_authority(scheme, host, port)

#
# Fixtures
#

@pytest.fixture
def root_uri():
    """A fixture that returns the root URI of the server being tested."""
    return make_root("wss" if (SCHEME == "https") else "ws")
