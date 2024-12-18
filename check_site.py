from os import environ
from datetime import datetime, timezone
from sys import argv, exit
import csv
from socket import create_connection
from socks import socksocket, HTTP
from urllib.parse import urlparse
from ssl import create_default_context
from time import mktime, strptime
from itertools import chain
from http.client import HTTPConnection, HTTPSConnection

USER_AGENT = "Python http.client"
TIMEOUT = 8
CSV_FILE = "results.csv"


def detect_proxy(protocol: str = None) -> dict:

    if not (proxy := environ.get('proxy')):
        proxy = environ.get('PROXY')
    if not proxy:
        for p in ["http", "https"]:
            if not (proxy := environ.get(f"{p}_proxy")):
                proxy = environ.get(f"{p.upper()}_PROXY")

    if proxy:
        _ = proxy[7:].split(":")
        _ = {'host': str(_[0]), 'port': int(_[1])}
        print("Proxy detected:", _)
        return _

    return {}


def probe(host: str, port: int = 443, path: str = "/", scheme: str = "https") -> dict:

    address = (str(host), int(port))
    headers = {'Host': address[0], 'User-agent': USER_AGENT}
    ssl_context = None
    tls_info = None

    if proxy := detect_proxy(scheme):
        if scheme == "https":
            socket = socksocket()
            print("Connecting to ", address, "using socket", socket)
            socket.set_proxy(HTTP, proxy['host'], port=proxy['port'])
            socket.connect(address)
            socket.close()
        #print(f"Proxy detected: {proxy['host']}:{proxy['port']}")
        if scheme == "https":
            conn = HTTPSConnection(proxy['host'], port=proxy['port'], timeout=TIMEOUT)
            conn.set_tunnel(host, port=port)
        else:
            conn = HTTPConnection(proxy['host'], port=proxy['port'], timeout=TIMEOUT)
    else:
        socket = create_connection(address=address, timeout=TIMEOUT)
        #print("No proxy detected")
        match scheme:
            case "http":
                conn = HTTPConnection(host, port=port, timeout=TIMEOUT)
            case "https":
                ssl_context = create_default_context()
                conn = HTTPSConnection(host, port=port, timeout=TIMEOUT, context=ssl_context)
                ssl_socket = ssl_context.wrap_socket(socket, server_hostname=host)
                tls_info = ssl_socket.version()
                cert_details = ssl_socket.getpeercert()
                print(cert_details)
                cert_issued_timestamp = round(mktime(strptime(cert_details['notBefore'], "%b %d %H:%M:%S %Y %Z")))
                cert_expiration_timestamp = round(mktime(strptime(cert_details['notAfter'], "%b %d %H:%M:%S %Y %Z")))
                common_names = [_[1] for _ in list(chain(*cert_details['subject'])) if 'commonName' in _]
                # print(tls_info, common_names[0], cert_expiration_timestamp)
            case _:
                raise Exception(f"Unhandled scheme type: '{scheme}'")

    print("path:", path)
    conn.request(method="GET", url=path, headers=headers)
    response = conn.getresponse()
    conn.close()

    return {
        'status': response.status,
        'reason': response.reason,
        'tls_info': tls_info,
    }


def write_csv(data: list, csv_file: str = CSV_FILE):

    fp = open(csv_file, 'a', newline='')
    writer = csv.writer(fp)
    #writer.writerow(data[0].keys())
    _ = [writer.writerow(row.values()) for row in data]
    fp.close()


def main(url: str) -> dict:

    if not ("://" in url):
        if ":80/" in url or url.endswith(":80"):
            url = f"http://{url}"
        else:
            url = f"https://{url}"
    #print("url:", url)
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
    #print(f"Probing: {scheme}://{host}:{port}{path}")
    result = probe(host, port, path, scheme)
        
    _ = {
        'timestamp': str(timestamp).split(".")[0],
        #'host': host,
        'url': url,
        'port': port,
        'status': result.get('status', "UNKNOWN"),
        'reason': result.get('reason', "UNKNOWN"),
        'tls_info': result.get('tls_info', "UNKNOWN"),
    }
    write_csv([_])
    return _


if __name__ == "__main__":

    if len(argv) < 2:
        exit(f"Usage: {argv[0]} <target>")
    _ = main(argv[1])
    print(_)

