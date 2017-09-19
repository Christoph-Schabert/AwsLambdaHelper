import json
import logging

try:
    from urllib.request import build_opener, Request, HTTPHandler
except ImportError:
    from urllib2 import build_opener, Request, HTTPHandler
from lambda_utils.response_handlers import BaseResponseHandler

FAILED = 'FAILED'
SUCCESS = 'SUCCESS'


class Cloudformation(BaseResponseHandler):
    def on_execution(self, event):
        try:
            self.event = json.loads(event['Records'][0]['Sns']['Message'])
        except:
            self.event = event
        return BaseResponseHandler.on_execution(self, event)

    def on_exception(self, ex):
        logging.exception(str(ex))
        send_signal(self.event, FAILED, str(ex))


def send_signal(event, response_status, reason, response_data=None):
    response_body = json.dumps(
        {
            'Status': response_status,
            'Reason': str(reason or 'ReasonCanNotBeNone'),
            'PhysicalResourceId': event.get('PhysicalResourceId', event['LogicalResourceId']),
            'StackId': event['StackId'],
            'RequestId': event['RequestId'],
            'LogicalResourceId': event['LogicalResourceId'],
            'Data': response_data or {}
        },
        sort_keys=True,
    )
    logging.debug(response_body)
    opener = build_opener(HTTPHandler)
    request = Request(event['ResponseURL'], data=response_body)
    request.add_header('Content-Type', '')
    request.add_header('Content-Length', len(response_body))
    request.get_method = lambda: 'PUT'
    opener.open(request)
