from squid_log_viewer import get_squid_data
import traceback
import json
from urllib import parse


def application(environ, start_response):

    response_headers = [('Content-type', 'text/plain')]

    try:

        query_params: dict = {}
        if '?' in environ.get('RAW_URI', '/'):
            query_params = dict(parse.parse_qsl(parse.urlsplit(environ['RAW_URI']).query))

        data = get_squid_data(query_params)
        json_data = json.dumps(data, default=str).encode('utf-8')
        del data

        response_headers = [
            ('Content-type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Cache-Control', 'no-cache, no-store'),
            ('Pragma', 'no-cache'),
            ('Content-Length', str(len(json_data))),
        ]
        start_response('200 OK', response_headers)
        return [json_data]

    except:

        start_response('500 Internal Server Error', response_headers)
        return [str(traceback.format_exc()).encode('utf-8')]
