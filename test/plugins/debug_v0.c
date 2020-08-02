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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

EXPORT WebSocketPlugin *CALLBACK debug_init(void);

static void *CALLBACK on_connect(const WebSocketServer *server);
static size_t CALLBACK on_message(void *, const WebSocketServer *, int,
                                  unsigned char *, size_t);

static WebSocketPlugin plugin = {
    sizeof(WebSocketPlugin),
    WEBSOCKET_PLUGIN_VERSION_0,
    NULL, /* destroy */
    on_connect,
    on_message,
    NULL, /* on_disconnect */
};

extern EXPORT WebSocketPlugin *CALLBACK debug_init(void) { return &plugin; }

static void choose_subprotocol(const WebSocketServer *);
static int send_uint(const WebSocketServer *, unsigned int);

static void *CALLBACK on_connect(const WebSocketServer *server)
{
    choose_subprotocol(server);

    /* Set a static response header. */
    server->header_set(server, "X-Debug-Header", "true");

    return (void *) 1;
}

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
    else if ((buffer_size >= 8) && !strncmp(msg, "header: ", 8)) {
        const char *value;

        {
            /* The header value must be null-terminated before retrieval. */
            size_t header_len = buffer_size - 8;
            char *header = malloc(header_len + 1);

            if (!header) {
                return 0;
            }

            memcpy(header, msg + 8, header_len);
            header[header_len] = '\0';

            value = server->header_get(server, header);

            free(header);
        }

        if (!value) {
            value = "<null>";
        }

        server->send(server, MESSAGE_TYPE_TEXT, (unsigned char *) value,
                     strlen(value));
    }
    else if ((buffer_size == 7) && !strncmp(msg, "version", buffer_size)) {
        if (!send_uint(server, server->version)) {
            return 0;
        }
    }
    else if ((buffer_size == 11) && !strncmp(msg, "proto-count", buffer_size)) {
        unsigned int count = (unsigned int) server->protocol_count(server);

        if (!send_uint(server, count)) {
            return 0;
        }
    }

    return buffer_size;
}

static void choose_subprotocol(const WebSocketServer *server)
{
    const char *index_str;
    long int index;
    char *end;
    const char *subprotocol;

    /* The test client may ask us to choose a subprotocol via request header. */
    index_str = server->header_get(server, "X-Choose-Subprotocol");
    if (!index_str || !index_str[0]) {
        return;
    }

    index = strtol(index_str, &end, 10);
    if (*end != '\0') {
        return; /* invalid integer */
    }

    if (index >= server->protocol_count(server)) {
        return; /* out of range */
    }

    subprotocol = server->protocol_index(server, index);
    server->protocol_set(server, subprotocol);
}

static int send_uint(const WebSocketServer *server, unsigned int u)
{
    char buf[20] = {0};
    int written;

    written = snprintf(buf, sizeof(buf), "%u", u);
    if ((written < 0) || (written >= sizeof(buf))) {
        return 0;
    }

    server->send(server, MESSAGE_TYPE_TEXT, (unsigned char *) buf, strlen(buf));
    return 1;
}
