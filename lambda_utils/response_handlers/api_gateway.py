import json
import logging

from concurrent.futures import TimeoutError

from lambda_utils.response_handlers import BaseResponseHandler

try:
    from urllib.parse import parse_qs
except ImportError:
    from urlparse import parse_qs


class ApiGateway(BaseResponseHandler):
    def on_execution(self, event):
        event['body'] = extract_body(event)
        return event

    def on_exception(self, ex):
        logging.exception(str(ex))
        if type(ex) == TimeoutError:
            return http_response("Execution is about to timeout.", status=504)
        else:
            return http_response('Internal Server Error', status=500)


def http_response(body, status=200, headers=None):
    default_headers = {'Access-Control-Allow-Origin': '*'}

    if headers:
        merged_headers = default_headers.copy()
        merged_headers.update(headers)
        headers = merged_headers
    else:
        headers = default_headers

    return {'statusCode': status, 'body': body, 'headers': headers}


def json_http_response(body, status=200, headers=None):
    json_body = json.dumps(body, sort_keys=True, indent=4, separators=(',', ': '))

    return http_response(json_body, status, headers)


def redirect_to(url, status=302):
    return http_response('', status=status, headers={'Location': url})


def extract_body(event):
    def content_type():
        headers = event.get('headers', {})
        for key in ['Content-Type', 'content-type']:
            if key in headers:
                return headers[key]
        return ''

    body = event.get('body')

    if 'application/json' in content_type():
        body = json.loads(event.get('body') or '{}')

    if 'application/x-www-form-urlencoded' in content_type():
        body = parse_qs(event.get('body') or '', keep_blank_values=True)

    return body
