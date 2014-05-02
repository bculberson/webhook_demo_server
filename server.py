#!/usr/bin/env python

# you can verify you have everything setup properly with
# curl -X POST -H "Content-Type: application/json" -d '{"object_id":"0","ts":"..."}' http://localhost:8888/a/callback/echo

import logging
import tornado.escape
import tornado.ioloop
import tornado.web
import os.path
import uuid
import datetime

from tornado.options import define, options, parse_command_line

define("port", default=8888, help="run on the given port", type=int)


class NotificationBuffer(object):
    def __init__(self):
        self.waiters = set()
        self.cache = []
        self.cache_size = 200

    def wait_for_notifications(self, callback, cursor=None):
        if cursor:
            new_count = 0
            for msg in reversed(self.cache):
                if msg["id"] == cursor:
                    break
                new_count += 1
            if new_count:
                callback(self.cache[-new_count:])
                return
        self.waiters.add(callback)

    def cancel_wait(self, callback):
        self.waiters.remove(callback)

    def new_notifications(self, notifications):
        logging.info("Sending new notification to %r listeners", len(self.waiters))
        for callback in self.waiters:
            try:
                callback(notifications)
            except:
                logging.error("Error in waiter callback", exc_info=True)
        self.waiters = set()
        self.cache.extend(notifications)
        if len(self.cache) > self.cache_size:
            self.cache = self.cache[-self.cache_size:]


global_message_buffer = NotificationBuffer()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", notifications=global_message_buffer.cache)


class CallbackHandler(tornado.web.RequestHandler):
    def check_xsrf_cookie(self):
        pass

    def post(self):
        notification = {
            "id": str(uuid.uuid4()),
            "json": self.request.body,
        }
        notification["html"] = tornado.escape.to_basestring(self.render_string("notification.html",
                                                                               notification=notification))
        global_message_buffer.new_notifications([notification])


class CallbackTimeoutHandler(tornado.web.RequestHandler):
    def check_xsrf_cookie(self):
        pass

    @tornado.web.asynchronous
    def post(self):
        def delayed_response():
            logging.warn("delayed response")
            self.finish()
        tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=10), delayed_response)


class CallbackErrorHandler(tornado.web.RequestHandler):
    def check_xsrf_cookie(self):
        pass

    def post(self):
        logging.warn("error response")
        self.set_status(500)


class CallbackWatcher(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        cursor = self.get_argument("cursor", None)
        global_message_buffer.wait_for_notifications(self.on_new_notifications, cursor=cursor)

    def on_new_notifications(self, notifications):
        # Closed client connection
        if self.request.connection.stream.closed():
            return
        self.finish(dict(notifications=notifications))

    def on_connection_close(self):
        global_message_buffer.cancel_wait(self.on_new_notifications)


if __name__ == "__main__":
    parse_command_line()
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/a/callback/echo", CallbackHandler),
            (r"/a/callback/timeout", CallbackTimeoutHandler),
            (r"/a/callback/error", CallbackErrorHandler),
            (r"/a/watch", CallbackWatcher),
        ],
        cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        xsrf_cookies=True,
    )
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
