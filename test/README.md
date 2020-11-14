# Testing with Autobahn

This test script makes use of
[Autobahn|TestSuite](http://autobahn.ws/testsuite/).

## Prerequisites

* Python 2.7.x (TestSuite doesn't do Python 3 yet)
* Python 3.6+ (for the remaining tests)
* [pip](https://pip.pypa.io/)
* \[Linux\] GNU Autotools (or just run the test server and each test suite
  manually)
* \[Windows\] PowerShell 2.0 (or greater)

## Setup

_Autobahn|TestSuite makes this a little more complicated than it needs to be.
My setup currently involves installing `wstest` on my system's Python 2 stack,
then activating a Python 3 virtualenv and installing the remaining requirements.
This should be easier once TestSuite supports Python 3._

### Autobahn|TestSuite

Because TestSuite doesn't support Python 3 yet, you'll need a separate
Python 2 stack (or virtualenv) with which to install the tool. Install the
`wstest` executable via

    $ [sudo] pip install autobahntestsuite

or

    $ pip install --user autobahntestsuite

and ensure that the mod_websocket test suite can find it in your `PATH`:

    $ which wstest
    ~/.local/bin/wstest

### Other Tests

The remaining required Python 3 packages are listed in requirements.txt. On
Linux, you can install them by executing the following from this directory:

    $ [sudo] pip3 install -r requirements.txt

If you don't want to install globally, you can alternatively run

    $ pip3 install -r requirements.txt --user
    $ export PATH=$PATH:$HOME/.local/bin

or install via `virtualenv` or similar. See your pip/virtualenv documentation
for other installation options.

## Testing

### Linux/Autotools

After you have installed the prerequisites, run

    $ make check

from the top-level directory. The test suite is large, so it may take a few
minutes to run. The results will be parsed and output as a
[TAP](http://testanything.org) stream.

If you want to just get the TAP output itself so you can pipe it into your
favorite [TAP consumer](http://testanything.org/consumers.html), run the
following *after* you have already run the test suite once and generated the
`test/test-results` folder:

    $ make start-test-server
    $ cd test
    $ ./aggregate.py

This will output the results again without re-running the Autobahn test suite.
Remember to stop the standalone test server afterwards with

    $ cd ..
    $ make stop-test-server

### Windows

For now, the test suite can only be run automatically with Linux and GNU
Autotools; Windows requires additional manual work.

Install the Python prerequisites (see the Setup section, above) and build both
the module and the example plugins (if using CMake, make sure `BUILD_EXAMPLES`
is true when you generate the build). Open a command prompt from the `test`
directory and run

    > powershell -ExecutionPolicy Bypass -File setup-win-test.ps1 -ModuleDirectory MODULE_DIR -Version VERSION

where `MODULE_DIR` is the directory containing your installation's modules, and
`VERSION` is either '2.2' or '2.4' depending on your installed httpd. For
example:

    > powershell -ExecutionPolicy Bypass -File setup-win-test.ps1 -ModuleDirectory "C:\Program Files\Apache Software Foundation\Apache2.4\modules" -Version 2.4

_Note that the `-ExecutionPolicy Bypass` argument indicates to PowerShell that
you trust the `setup-win-test.ps1` script to run on your system. If you don't
trust it, don't run it..._

This script generates a test configuration and several supporting test
directories. Copy `mod_websocket.so` and the example plugins into the
`test/httpd/modules` directory that is created, and launch httpd with the
generated configuration:

    > httpd -d "WEBSOCKET_DIR\test\httpd" -f test.conf

where `WEBSOCKET_DIR` is the full path to your apache-websocket folder.

Open a new prompt (since httpd will be running in the old one), change back to
the `tests` directory, and run the Autobahn test suite with

    > wstest -m fuzzingclient && python present.py

Then run mod_websocket's pytest suite with

    > py.test

Once the test suite has completed, you can stop the temporary httpd instance in
your first prompt window with Ctrl-C.

## Adding Tests

New pytest suites can be added directly to the `pytest/` directory.

If you need to run a program that isn't pytest-based, add it to the `commands`
array in `tests.yaml`. Said program _must_ output valid TAP, version 13 or
prior.
