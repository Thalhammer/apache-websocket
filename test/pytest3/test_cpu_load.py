import asyncio

import psutil
import pytest
import websockets

from test_fixtures import root_uri

# The maximum CPU usage we consider acceptable.
MAX_CPU_PERCENTAGE = 50

#
# Helpers
#

def any_cpus_railed():
   """Returns True if any CPU cores have crossed the MAX_CPU_PERCENTAGE."""
   percentages = psutil.cpu_percent(interval=0.5, percpu=True)

   for p in percentages:
       if p > MAX_CPU_PERCENTAGE:
           return True

   return False

#
# Tests
#

pytestmark = pytest.mark.asyncio

@pytest.mark.skipif(any_cpus_railed(),
                    reason="current CPU load is too high to reliably test for spikes")
async def test_cpu_load_does_not_spike_when_idle(root_uri):
    """
    A regression test for issue #9 (railed CPU when a WebSocket connection is
    open but idle).
    """
    uri = root_uri + "/echo"

    async with websockets.connect(uri):
        # Now that the connection is open, see if any CPUs are in trouble.
        assert not any_cpus_railed()
