# apache-websocket

The apache-websocket module is an Apache 2.x server module that may be used to
process requests using the WebSocket protocol (RFC 6455) by an Apache 2.x
server. The module consists of a plugin architecture for handling WebSocket
messaging. Doing so does _not_ require any knowledge of internal Apache
structures.

This implementation supports protocol versions 7, 8, and 13.

## Download

    $ git clone git://github.com/jchampio/apache-websocket.git

## Building and Installation

Several build options are available.

### SCons

SCons may be used to build the module:

    $ scons
    $ sudo scons install

For Windows, do not include the word `sudo` when installing the module. Also,
the `SConstruct` file is hard-coded to look for the Apache headers and
libraries in `C:\Program Files\Apache Software Foundation\Apache2.2`. You
will need to install the headers and libraries when installing Apache. The
`Build Headers and Libraries` option is disabled by default, so you will have
to perform a `Custom` installation of Apache. Refer to the Apache document
entitled _Using Apache HTTP Server on Microsoft Windows_ for more information.

### apxs[2]

Alternatively, you may use `apxs` to build and install the module. Under Linux
(at least under Ubuntu), use:

    $ sudo apxs2 -i -a -c mod_websocket.c

You probably only want to use the `-a` option the first time you issue the
command, as it may overwrite your configuration each time you execute it (see
below).

You may use `apxs` under Mac OS X if you do not want to use SCons. In that
case, use:

    $ sudo apxs -i -a -c mod_websocket.c

### GNU Autotools (Linux-only)

If you're comfortable with autotools, configure and Makefile templates are
provided. This is the only supported way to run the builtin test suite on Linux;
see `test/README.md`.

If you've just cloned the repository, you'll need to run the following commands
once:

    $ ./autogen.sh         # creates the configure script
    $ ./configure          # adapts the build to your system

Thereafter, you can build/test/install with the usual trio:

    $ make                 # builds mod_websocket and the example plugins
    $ make check           # runs the built-in Python test suite
    $ [sudo] make install  # installs mod_websocket to httpd's modules directory

#### Configure Options

The configure script primarily cares about three programs in your installation:
`apxs`, `apachectl`, and `httpd`. It uses these programs to build and test the
module. By default it searches for these in your PATH, but to direct it to a
custom installation of your own, set the `APACHE_BINDIR` variable at configure
time:

    $ ./configure APACHE_BINDIR=/opt/apache2/bin

(You can also set all three paths separately; see `./configure --help`.)

The test suite also needs to enable a server MPM for the standalone test server.
If you have statically compiled an MPM into httpd, configure will use that;
otherwise it will use the first MPM DSO it finds installed in your modules
directory. To override its choice, use the `TEST_MPM` variable:

    $ ./configure TEST_MPM=worker

`TEST_MPM` accepts the name of any installed MPM module, or `'builtin'` to force
the use of a static MPM.

#### Other Helpful Rules

    $ make clean                             # removes the build artifacts
    $ [sudo] make install-examples           # installs the example plugins
    $ [sudo] make [start|stop|restart]       # starts/stops/restarts httpd via apachectl
    $ make [start|stop|restart]-test-server  # starts/stops/restarts the standalone test server
    $ make debug [DEBUGGER=program]          # starts the test server under DEBUGGER
                                             # (`gdb --args` by default)

### CMake (Windows-only)

An experimental `CMakeLists.txt` is provided for Windows CMake builds only. It
is based on the CMake implementation provided by Apache httpd and attempts to
follow its path conventions, so those already building httpd with CMake should
feel at home.  Make sure that the `CMAKE_INSTALL_PREFIX` is correctly set to
httpd's installation prefix when starting CMake, so that dependent libraries and
header locations are detected for you.

## Plugins

While the module is used to handle the WebSocket protocol, plugins are used to
implement the application-specific handling of WebSocket messages.

A plugin need only have one function exported that returns a pointer to an
initialized `WebSocketPlugin` structure. The `WebSocketPlugin` structure
consists of the structure size, structure version, and several function
pointers. The size should be set to the `sizeof` the `WebSocketPlugin`
structure, the version should be set to 0, and the function pointers should be
set to point to the various functions that will service the requests. The only
required function is the `on_message` function for handling incoming messages.

See `examples/mod_websocket_echo.c` for a simple example implementation of an
"echo" plugin. A sample `client.html` is included as well. If you try it and
you get a message that says Connection Closed, you are likely using a client
that does not support these versions of the protocol.

A more extensive example may be found in
`examples/mod_websocket_dumb_increment.c`. That plugin implements the
dumb-increment-protocol (see libwebsockets by Andy Green for more information
on the protocol). There is a test client for testing the module in
`increment.html`. It uses the WebSocket client API which supports passing
supported protocols in the WebSocket constructor. If your browser does not
support this, either upgrade your browser or modify the plugin so that it
doesn't verify the protocol.

If you provide an `on_connect` function, return a non-null value to accept the
connection, and null if you wish to decline the connection. The return value
will be passed to your other methods for that connection. During your
`on_connect` function, you may access the Apache `request_rec` structure if you
wish. You will have to include the appropriate Apache include files. If you do
not wish to do that, you may also access the headers (both input and output)
using the provided functions. There are also protocol-specific handling
functions for selecting the desired protocol for the WebSocket session. You may
only safely access the `send` or `close` functions in your `on_connect`
function from a separate thread, as the connection will not be completed until
you return from the function.

You may use `apxs`, SCons, or some other build system to be build and install
the plugins. Also, it does not need to be placed in the same directory as the
WebSocket module.

## Configuration

The `http.conf` file is used to configure WebSocket plugins to handle requests
for particular locations. Inside each `Location` block, set the handler, using
the `SetHandler` keyword, to `websocket-handler`. Next, add a
`WebSocketHandler` entry that contains two parameters. The first is the name of
the dynamic plugin library that will service the requests for the specified
location, and the second is the name of the function in the dynamic library
that will initialize the plugin.

Here is an example of the configuration changes to `http.conf` that are used to
handle the WebSocket plugin requests directed at `/echo` under Mac OS X. The
server will initialize the module by calling the `echo_init` function in
`mod_websocket_echo.so`:

    LoadModule websocket_module   libexec/apache2/mod_websocket.so

    <IfModule mod_websocket.c>
      <Location /echo>
        SetHandler websocket-handler
        WebSocketHandler libexec/apache2/mod_websocket_echo.so echo_init
      </Location>
      <Location /dumb-increment>
        SetHandler websocket-handler
        WebSocketHandler libexec/apache2/mod_websocket_dumb_increment.so dumb_increment_init
      </Location>
    </IfModule>

Under Linux, the module-specific configuration may be contained in a single
file called `/etc/apache2/mods-available/websocket.load` (your version of Linux
may vary). If you did not use `apxs2` with the `-a` option to initially
create the module, you will have to make a link between
`/etc/apache2/mods-enabled/websocket.load` and
`/etc/apache2/mods-available/websocket.load`. Take a look at the already enabled
modules to see how it should look. Since the directory containing the module is
different from Mac OS X, the configuration will look more like this:

    LoadModule websocket_module   /usr/lib/apache2/modules/mod_websocket.so

    <IfModule mod_websocket.c>
      <Location /echo>
        SetHandler websocket-handler
        WebSocketHandler /usr/lib/apache2/modules/mod_websocket_echo.so echo_init
      </Location>
    </IfModule>

This is the configuration that may be overwritten when the `-a` option is
included using `axps2`, so be careful.

Under Windows, the initialization function is of the form `_echo_init@0`, as it
is using the `__stdcall` calling convention:

    LoadModule websocket_module   modules/mod_websocket.so

    <IfModule mod_websocket.c>
      <Location /echo>
        SetHandler websocket-handler
        WebSocketHandler modules/mod_websocket_echo.so _echo_init@0
      </Location>
    </IfModule>

### `WebSocketMaxMessageSize`

_Note: in releases 0.1.1 and earlier, this directive was called
`MaxMessageSize`. It was renamed to properly namespace it with the other
directives._

Since we are dealing with messages, not streams, we need to specify a maximum
message size. The default size is 32 megabytes. You may override this value by
specifying a `WebSocketMaxMessageSize` configuration setting. Here is an example
of how to set the maximum message size is set to 64 megabytes:

    <IfModule mod_websocket.c>
      <Location /echo>
        SetHandler websocket-handler
        WebSocketHandler /usr/lib/apache2/modules/mod_websocket_echo.so echo_init
        WebSocketMaxMessageSize 67108864
      </Location>
    </IfModule>

If you are using extremely small values for `WebSocketMaxMessageSize`, be aware
that its limit also applies to control frame payloads. As an example, with a
`WebSocketMaxMessageSize` of 30, the maximum length of a close reason message
accepted by a server will be 28 bytes (2 bytes for the close code plus 28 for
the message reaches the limit of 30). Any larger payloads will result in a
closed connection. It's recommended that you go no lower than 125 (the maximum
size of a WebSocket control frame payload) to avoid closing the connection on
correctly implemented clients.

### `WebSocketOriginCheck`

The WebSocket protocol includes protection against cross-site request forgeries,
or CSRF -- occasionally referred to as CSWSH (Cross-Site WebSocket Hijacking) in
this context -- with its use of [the `Origin`
header](https://tools.ietf.org/html/rfc6454). The `Origin` header allows a
conforming user-agent to tell the server where a WebSocket connection is
originating from, so that the server may use this information to accept or
reject the incoming connection. This check prevents a malicious third-party
website from connecting to your WebSocket plugin using your users' credentials,
but it requires the server to know which origins are trusted.

The `WebSocketOriginCheck` directive controls how the server applies this
security feature. The three options are `Same`, which requires the `Origin` sent
by the user-agent to exactly match the origin of your WebSocket service;
`Trusted`, which checks the incoming `Origin` against a list that you provide;
and `Off`, which disables cross-origin protection entirely. The default is
`Same`.

_Note that in all cases, handshakes without an `Origin` header are allowed to
connect._

#### Same-Origin

Same-origin protection is the default mode; you can explicitly enable it using

    WebSocketOriginCheck Same

In effect, this checks that the `Origin` sent by the client has the same
scheme, hostname, and port number that are currently in use by the server.  If
_any_ of those three items differ, the handshake will be rejected. The result is
that Javascript served from the same server as your WebSocket plugin will be
able to connect, and everyone else will be blocked.

Some caveats:
* Same-origin mode will reject cross-scheme connections (http-to-wss and
  https-to-ws). This is probably what most users want, since allowing an
  unsecured HTTP resource to connect to a `wss://` service is a potential
  vulnerability for that service, and connecting to a `ws://` service from an
  HTTPS-secured page doesn't make a lot of sense. If your use case requires
  cross-scheme access, you must use `Trusted` mode instead.
* The origin of your WebSocket service URI is only strictly defined if your
  Apache configuration has a strictly defined `VirtualHost`. Put another way, if
  your service is hosted from a wildcard or "default" VirtualHost, it's possible
  that your service's origin will be partially defined by the handshake's `Host`
  header or by its request target -- both of which are controlled by the
  user-agent, not the server. In most cases this shouldn't be a problem, since
  malicious third parties should have no control over a user-agent's `Host`
  header and shouldn't be able to direct requests to an incorrect hostname. But
  if you'd prefer a more paranoid approach, switch to `Trusted` mode to
  explicitly list the origins that your plugin should respond to.

#### Trusted Origins

To specify a list of origins that your plugin will accept connections from, use
`WebSocketOriginCheck Trusted` and the `WebSocketTrustedOrigin` directive:

    WebSocketOriginCheck Trusted
    WebSocketTrustedOrigin https://www.example.com https://other.example.com
    WebSocketTrustedOrigin http://other.example.net:8080

If your WebSocket plugin can be accessed via multiple hostname aliases or ports,
each combination must be added as a separate entry, since the `Origin` value
sent by a user-agent must _exactly_ match one in the list to be allowed.

#### Disabling Origin Checks

The directive

    WebSocketOriginCheck Off

will completely disable checks on the `Origin` header and allow connections
through a user-agent from any website. As a general rule, this should only be
done if your WebSocket plugin provides a global service to anonymous users, and
those users have no reason to care if third parties can connect to that service
on their behalf. Otherwise, use of this directive opens your users to [hijacking
attacks](https://www.notsosecure.com/2014/11/27/how-cross-site-websocket-hijacking-could-lead-to-full-session-compromise/).
You have been warned.

### `WebSocketAllowReservedStatusCodes`

By default, the module will reject close frame status codes in the official
range (1000-2999) that are undefined/reserved for future use. You may use

    WebSocketAllowReservedStatusCodes On

to disable this protection, for instance when designing/testing an official
addition to the WebSocket protocol. *Use this feature responsibly;* production
systems should not generally enable it. Additionally, this feature does not
allow the use of explicitly prohibited codes (1005, 1006, etc.). It is not a
general "allow protocol violations" flag.

## Authors

* The original code was written by `self.disconnect`.

## License

Please see the file called LICENSE.
