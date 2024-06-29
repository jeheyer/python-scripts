#!/usr/bin/env python

from asyncio import gather, run, new_event_loop, open_connection, get_event_loop
from smtplib import SMTP
from time import time, mktime, strptime, localtime, timezone, altzone
from math import ceil
from ssl import create_default_context, SSLContext, PROTOCOL_TLS, PROTOCOL_TLS_CLIENT, PROTOCOL_TLSv1_2
from socket import gethostbyname, create_connection, getaddrinfo, gethostname, AI_CANONNAME, AF_INET
from aiodns import DNSResolver
from aiohttp import ClientSession
from getpass import getuser
from sys import argv
from aioopenssl import create_starttls_connection

CONNECT_TIMEOUT = 3
DAYS_THRESHOLD = 12
INPUT_FILE = "cert_hostnames.txt"
SMTP_HOSTNAME = "localhost"
SMTP_PORT = 25


def get_targets(input_file=INPUT_FILE):

    targets = []
    try:
        f = open(input_file, 'r')
    except:
        quit(f"Can't open file: '{input_file}")

    for line in f:
        if line.startswith('#') or line.startswith('\n'):
            continue
        else:
            targets.append(line.rstrip())
    f.close()
    return targets


async def check_site(target="localhost", port=443):

    site = {
        'hostname': target.split(":")[0] if ":" in target else target,
        'port': target.split(":")[1] if ":" in target else port,
        'status': "unknown",
        'cert': {},
    }

    # Verify hostname resolves in DNS
    try:
        site['ip_address'] = gethostbyname(site['hostname'])
    except Exception as e:
        site['status'] = f"Not resolvable in DNS"
        return site

    # Verify hostname is reachable
    try:
        #ssl_context = SSLContext() #PROTOCOL_TLS)
        ssl_context = create_default_context()
        #sock = create_connection((site['hostname'], str(site['port'])), timeout=CONNECT_TIMEOUT)
        reader = await open_connection(site['hostname'], site['port'], ssl=ssl_context)
    except Exception as e:
        site['status'] = f"Not reachable on port {site['port']}"
        return site

    # Attempt SSL connection
    try:
        #ssl_context = create_default_context()
        #ssock = ssl_context.wrap_socket(sock, server_hostname=site['hostname'])
        #start_tls(ssl_context, server_hostname=site['hostname'], ssl_handshake_timeout=CONNECT_TIMEOUT)
        async with ClientSession() as session:
            async with session.get(f"https://{site['hostname']}/") as r:
                if r.status:
                    site['status'] = int(r.status)
                    #cert_details = await r.connection.transport.get_extra_info('peercert')
                    cert_details = r.connection.transport._ssl_protocol._extra['ssl_object'].getpeercert(True)
                else:
                    site['status'] = "Not responding to HTTP request"

    except Exception as e:
        #site['info'] = f"TLS handshake to '{site['hostname']}' on port {site['port']} failed"
        #site['status'] = format(e)
        return site

    conn = await create_starttls_connection(loop=get_event_loop(), host="www.j5.org", port=443, server_hostname="www.j5.org")
    print(conn)

    """

    # Attempt to get certificate details
    #try:
    #    cert_details = ssock.getpeercert()
    #except:
    #    site['info'] = f"Cannot get certificate details for '{site['hostname']}' on port {site['port']} "
    #    return site

    #print(cert_details)
    # Get original issue and expiration timestamps
    site['cert']['issued_timestamp'] = round(mktime(strptime(cert_details['notBefore'], "%b %d %H:%M:%S %Y %Z")));
    site['cert']['expiration_timestamp'] = round(mktime(strptime(cert_details['notAfter'], "%b %d %H:%M:%S %Y %Z")));

    # Adjust for local timezone setting
    local_timezone_offset = timezone if (localtime().tm_isdst == 0) else altzone
    current_timestamp = round(time()) + local_timezone_offset

    # Do math to determine days, hour, seconds remaining until expiration
    site['cert']['seconds_until_expiration'] = site['cert']['expiration_timestamp'] - current_timestamp
    site['cert']['hours_until_expiration'] = ceil(site['cert']['seconds_until_expiration'] / 3600)
    site['cert']['days_until_expiration'] = site['cert']['hours_until_expiration'] // 24

    """

    return site


async def main():

    if len(argv) < 2:
        quit(f"Usage: {argv[0]} 'hostnames_file'")
    input_file = argv[1]
    recipient = None
    if len(argv) > 2:
        recipient = argv[2]
    if len(argv) > 3:
        sender = argv[3]
    else:
        sender = getuser() + "@" + getaddrinfo(gethostname(), 0, flags=AI_CANONNAME)[0][3]

    targets = get_targets(input_file)
    tasks = [check_site(target) for target in targets]
    results = await gather(*tasks)
    for result in results:
        print(result)
    output = ""
    for result in results:
        if 'info' in result:
            output += result.get('info') + '\n'
        if days_until_expiration := result['cert'].get('days_until_expiration', 365) <= DAYS_THRESHOLD:
            if days_until_expiration <= 1:
                output += str(result['cert']['hours_until_expiration']) + " hours!!!\n"
            else:
                output += str(result['cert']['days_until_expiration']) + " days\n"

    if recipient and output:
        subject = "An SSL certificate is expiring soon!"
        message = f"From: {sender}\nTo: {recipient}\nSubject: {subject}\n{output}"
        try:
            server = SMTP(SMTP_HOSTNAME, port=SMTP_PORT)
            server.ehlo()
            server.sendmail(sender, recipient, message)
            server.quit()
        except Exception as e:
            print(e)
    else:
        print(output, end='')


if __name__ == "__main__":
    run(main())
