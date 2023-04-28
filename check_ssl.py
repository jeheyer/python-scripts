#!/usr/bin/env python3

from sys import argv
from ssl import create_default_context
from socket import create_connection
from pprint import pprint


def main():

    if len(argv) > 1:
        hostname = argv[1]
    else:
        quit(f"Usage: {argv[0]} <site hostname>")

    info = {'status': None, 'tls_version': "UNKNOWN", 'cert_details': None}

    try:
        ssl_context = create_default_context()
        sock = create_connection((hostname, "443"), timeout=3)
        ssock = ssl_context.wrap_socket(sock, server_hostname=hostname)
        info['status'] = "OK"
        info['tls_version'] = ssock.version()
        info['cert_details'] = ssock.getpeercert()
    except Exception as e:
        quit(e)

    pprint(info)


if __name__ == "__main__":

    main()
