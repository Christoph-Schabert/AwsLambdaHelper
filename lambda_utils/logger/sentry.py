import logging
import os

from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler
from raven.transport.requests import RequestsHTTPTransport

from . import BaseLogger


class Sentry(BaseLogger):
    client = None

    def on_init(self, function):
        self.client = Client(dsn=os.environ['SENTRY_IO'], transport=RequestsHTTPTransport, name=os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
        self.handler = SentryHandler(client=self.client, level=logging.ERROR)
        setup_logging(self.handler)
        BaseLogger.on_init(self, function)

    def on_execution(self, event):
        self.add_user_context(event)
        self.add_x_ray_tags(event)
        BaseLogger.on_execution(self, event)

    def add_user_context(self, event):
        try:
            user_context = {}
            for key, value in event['requestContext']['authorizer'].items():
                user_context[key.lower()] = value
            self.client.user_context(user_context)
        except KeyError:
            logging.debug("No user  context recognized in event['requestContext']['authorizer']")

    def add_x_ray_tags(self, event):
        try:
            if '_X_AMZN_TRACE_ID' in os.environ:
                self.client.tags_context({'X-Amzn-Trace-Id': os.environ['_X_AMZN_TRACE_ID']})

            if 'X-Amzn-Trace-Id' in event.get('headers', {}):
                request_trace_id = event['headers']['X-Amzn-Trace-Id']
                for trace_id in request_trace_id.split(';'):
                    if 'Root' in trace_id or 'root' in trace_id:
                        self.client.tags_context({os.environ.get('SourceTraceId', 'Request-X-Amzn-Trace-Id'): trace_id})
        except KeyError:
            logging.debug("No request x-ray-trace-id recognized in event[u'headers'][u'X-Amzn-Trace-Id']")
