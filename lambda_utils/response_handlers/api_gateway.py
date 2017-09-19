from lambda_utils.response_handlers import BaseResponseHandler
from concurrent.futures import TimeoutError
from cStringIO import StringIO
import gzip
import json
try:
    from urllib.parse import parse_qs
except ImportError:
    from urlparse import parse_qs


class ApiGateway(BaseResponseHandler):
    gzip_response = None
    event = []

    def __init__(self, gzip_response=True):
        self.gzip_response = gzip_response

    def on_execution(self, event):
        event['body'] = extract_body(event)
        self.event = event
        return event

    def on_exception(self, ex):
        if type(ex) == TimeoutError:
            return http_response("Execution is about to timeout.", status=504)
        else:
            return http_response('Internal Server Error', status=500)

    def on_response(self, response):
        response = self._gzip_if_possible(response)

        return response

    def _gzip_if_possible(self, response):
        accecpted_encoding = self.event.get('headers', {}).get('Accept-Encoding', '')
        if 'gzip' not in accecpted_encoding.lower():
            return response

        if response['statusCode'] < 200 or response['statusCode'] >= 300 or 'Content-Encoding' in response['headers']:
            return response

        gzip_buffer = StringIO()
        gzip_file = gzip.GzipFile(mode='wb', fileobj=gzip_buffer)
        gzip_file.write(response.get('body'))
        gzip_file.close()

        response['body'] = gzip_buffer.getvalue()
        response['headers']['Content-Encoding'] = 'gzip'
        response['headers']['Vary'] = 'Accept-Encoding'
        response['headers']['Content-Length'] = len(response['body'])
        return response


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
