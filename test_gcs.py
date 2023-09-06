import http.client
import ssl
import os

BUCKET_NAME = "public-j5-org"

try:
    host = BUCKET_NAME + ".storage.googleapis.com"
    if https_proxy := os.environ.get('HTTPS_PROXY'):
        proxy_host, proxy_port = https_proxy[7:].split(":")
        conn = http.client.HTTPSConnection(proxy_host, port=proxy_port, timeout=1)
        conn.set_tunnel(host)
    else:
        ssl_context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(host, port=443, timeout=1, context=ssl_context)
    conn.request(method="GET", url="/", headers={'User-agent': "Python http.client"})
    response = conn.getresponse()
    print("HTTP status code:", response.status)
except Exception as e:
    print(e)

conn.close()
