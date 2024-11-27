from os import environ
from datetime import datetime, timezone
from sys import argv, exit
from urllib.parse import urlparse
from ssl import create_default_context
from http.client import HTTPConnection, HTTPSConnection

USER_AGENT = "Python http.client"
TIMEOUT = 8


def detect_proxy(protocol: str = None) -> dict:

    if not (proxy := environ.get('proxy')):
        proxy = environ.get('PROXY')
    for p in ["http", "https"]:
        if not (proxy := environ.get(f"{p}_proxy")):
            proxy = environ.get(f"{p}_PROXY")

    if proxy:
        _ = proxy[7:].split(":")
        return {'host': _[0], 'port': _[1]}

    return {}


def probe(host: str, port: int = 443, path: str = "/", scheme: str = "https") -> dict:

    if proxy := detect_proxy(scheme):
        print(f"Proxy detected: {proxy['host']}:{proxy['port']}")
        conn = HTTPConnection(proxy['host'], port=proxy['port'], timeout=TIMEOUT)
        conn.set_tunnel(host, port=port)
    else:
        print("No proxy detected")
        match scheme:
            case "http":
                conn = HTTPConnection(host, port=port, timeout=TIMEOUT)
            case "https":
                ssl_context = create_default_context()
                conn = HTTPSConnection(host, port=port, timeout=TIMEOUT, context=ssl_context)
            case _:
                conn = None

    #print("Network Connection to https://{}:{} successful!".format(host, port))
    conn.request(method="GET", url=path, headers={'User-agent': USER_AGENT})
    response = conn.getresponse()
    conn.close()

    return {
        'status': response.status,
        'reason': response.reason,
    }


def main(url: str) -> dict:

    if not ("://" in url):
        if ":80/" in url or url.endswith(":80"):
            url = f"http://{url}"
        else:
            url = f"https://{url}"
    print("url:", url)
    _ = urlparse(url)
    scheme = str(_.scheme).lower()
    host = str(_.hostname)
    if not (port := _.port):
        match scheme:
            case "http":
                port = 80
            case "https":
                port = 443
            case _:
                port = 443
    path = _.path if _.path else "/"
    timestamp = datetime.now(timezone.utc)
    print(f"Probing: {scheme}://{host}:{port}{path}")
    result = probe(host, port, path, scheme)
        
    return {
        'timestamp': str(timestamp).split(".")[0],
        'host': host,
        'port': port,
        'status': result.get('status', "UNKNOWN"),
        'reason': result.get('reason', "UNKNOWN"),
    }


if __name__ == "__main__":

    if len(argv) < 2:
        exit(f"Usage: {argv[0]} <target>")
    _ = main(argv[1])
    print(_)
