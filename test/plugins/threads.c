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

#include <stdlib.h>

#include "apr_atomic.h"
#include "apr_thread_proc.h"
#include "httpd.h"

/*
 * The threads plugin starts a number of threads, all of which independently
 * count backwards from 1000 and send that count over the WebSocket connection.
 * After every thread has finished, the connection is closed.
 */

EXPORT WebSocketPlugin *CALLBACK threads_init(void);

static void *CALLBACK on_connect(const WebSocketServer *);
static size_t CALLBACK on_message(void *, const WebSocketServer *, int,
                                  unsigned char *, size_t);
static void CALLBACK on_disconnect(void *, const WebSocketServer *);

static WebSocketPlugin plugin = {
    sizeof(WebSocketPlugin),
    WEBSOCKET_PLUGIN_VERSION_0,
    NULL, /* destroy */
    on_connect,
    on_message,
    on_disconnect,
};

extern EXPORT WebSocketPlugin *CALLBACK threads_init(void) { return &plugin; }

/*
 * Plugin Implementation
 */

struct plugin_data
{
    apr_pool_t *pool;
    const WebSocketServer *server;
    apr_thread_t **threads;         /* NULL-terminated list */
    volatile apr_uint32_t active;   /* how many threads are still running? */
    volatile apr_uint32_t stopping; /* set to 1 when threads should stop */
};

struct thread_data
{
    struct plugin_data *plugin;
    int index;
    int count;
};

static void *APR_THREAD_FUNC thread_main(apr_thread_t *, void *);

static void *CALLBACK on_connect(const WebSocketServer *server)
{
    request_rec *r;
    struct plugin_data *data;
    int i;
    static const int num_threads = 10;

    r = server->request(server);
    if (!r) {
        return NULL;
    }

    data = apr_pcalloc(r->pool, sizeof(*data));
    data->server = server;
    data->active = num_threads;

    /* Create a pool for use by the plugin. */
    if (apr_pool_create(&data->pool, r->pool) != APR_SUCCESS) {
        return NULL;
    }
    apr_pool_tag(data->pool, "threads websocket plugin");

    /* Create the threads array. Leave an extra NULL at the end. */
    data->threads =
        apr_pcalloc(data->pool, sizeof(*data->threads) * (num_threads + 1));

    /* Start each thread in the list. */
    for (i = 0; i < num_threads; ++i) {
        apr_status_t err;
        struct thread_data *tdata;

        tdata = apr_pcalloc(data->pool, sizeof(*tdata));
        tdata->plugin = data;
        tdata->index = i;
        tdata->count = 1000;

        err = apr_thread_create(&data->threads[i], NULL, thread_main, tdata,
                                data->pool);
        if (err) {
            return NULL;
        }
    }

    return data;
}

static void CALLBACK on_disconnect(void *vdata, const WebSocketServer *server)
{
    struct plugin_data *data = vdata;
    apr_thread_t **thread;

    /* Tell the threads to stop. */
    apr_atomic_inc32(&data->stopping);

    /* Wait for every thread before returning control. */
    for (thread = data->threads; *thread; thread++) {
        apr_status_t ret;
        apr_thread_join(&ret, *thread);
    }
}

static size_t CALLBACK on_message(void *private, const WebSocketServer *server,
                                  int type, unsigned char *buf, size_t bufsize)
{
    /* Ignore all incoming messages. */
    return bufsize;
}

/*
 * Counter Threads
 */

static void *APR_THREAD_FUNC thread_main(apr_thread_t *t, void *vdata)
{
    struct thread_data *tdata = vdata;
    const WebSocketServer *server = tdata->plugin->server;
    char buf[100];

    while (tdata->count && !apr_atomic_read32(&tdata->plugin->stopping)) {
        size_t written;

        /* Send a message containing the current thread's index and count. */
        written =
            snprintf(buf, sizeof(buf), "%d: %d", tdata->index, tdata->count);
        if (written < 0 || written >= sizeof(buf)) {
            return NULL;
        }

        server->send(server, MESSAGE_TYPE_TEXT, (unsigned char *) buf, written);

        tdata->count--;
    }

    if (apr_atomic_dec32(&tdata->plugin->active) == 0) {
        /* Last thread to complete. Close the connection. */
        static const unsigned short status = 1000;
        unsigned char buf[2];

        buf[0] = (status >> 8) & 0xFF;
        buf[1] = (status >> 0) & 0xFF;

        server->send(server, MESSAGE_TYPE_CLOSE, buf, sizeof(buf));
    }

    return NULL;
}
