/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "websocket_plugin.h"

#include <string.h>

EXPORT WebSocketPlugin *CALLBACK debug_init(void);

static size_t CALLBACK on_message(void *, const WebSocketServer *, int,
                                  unsigned char *, size_t);

static WebSocketPlugin plugin = {
    sizeof(WebSocketPlugin),
    WEBSOCKET_PLUGIN_VERSION_0,
    NULL, /* destroy */
    NULL, /* on_connect */
    on_message,
    NULL, /* on_disconnect */
};

extern EXPORT WebSocketPlugin *CALLBACK debug_init(void) { return &plugin; }

static size_t CALLBACK on_message(void *private, const WebSocketServer *server,
                                  int type, unsigned char *buffer,
                                  size_t buffer_size)
{
    char *msg;

    if (type != MESSAGE_TYPE_TEXT) {
        return buffer_size;
    }

    msg = (char *) buffer;

    if ((buffer_size == 5) && !strncmp(msg, "close", buffer_size)) {
        server->close(server);
    }

    return buffer_size;
}
