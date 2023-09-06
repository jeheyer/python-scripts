import http.client
import ssl
import os

BUCKET_NAME = "public-j5-org"
GCS_PORT = 443
CONN_TIMEOUT = 3

try:
    host = BUCKET_NAME + ".storage.googleapis.com"
    if https_proxy := os.environ.get('HTTPS_PROXY'):
        proxy_host, proxy_port = https_proxy[7:].split(":")
        print("Proxy detected: {}:{}".format(proxy_host, proxy_port))
        conn = http.client.HTTPSConnection(proxy_host, port=proxy_port, timeout=CONN_TIMEOUT)
        conn.set_tunnel(host, port=GCS_PORT)
    else:
        ssl_context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(host, port=GCS_PORT, timeout=CONN_TIMEOUT, context=ssl_context)
    print("Network Connection to https://{}:{} successful!".format(host, GCS_PORT))
    conn.request(method="GET", url="/", headers={'User-agent': "Python http.client"})
    response = conn.getresponse()
    print("HTTP status code:", response.status)
except Exception as e:
    print(e)

conn.close()
