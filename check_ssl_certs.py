#!/usr/bin/env python

# Just in case still running on Python2
from __future__ import print_function

from smtplib import SMTP
from sys import exit, argv
from getpass import getuser
from socket import create_connection, gethostname, gethostbyname, getaddrinfo, getaddrinfo, AI_CANONNAME
from ssl import create_default_context
from math import ceil
from time import time, localtime, timezone, altzone, mktime, strptime

DAYS_THRESHOLD = 12
INPUT_FILE = "cert_hostnames.txt"


class Target:

    def __init__(self, target: str, port: int = 443):

        if ":" in target:
            self.hostname, self.port = target.split(":")
        else:
            self.hostname = target
            self.port = port

        self.is_resolvable = False
        self.is_reachable = False

        # Verify hostname resolves in DNS
        try:
            gethostbyname(self.hostname)
            self.is_resolvable = True
        except:
            self.is_resolvable = False

        # Verify hostname is reachable on port 443
        try:
            sock = create_connection((self.hostname, str(self.port)), timeout=3)
            self.is_reachable = True
        except:
            self.is_reachable = False


class SSLCert:

    def __init__(self, hostname):

        self.hostname = hostname
        self.common_name = hostname

        # Retrieve details for the certificate
        self.is_valid, self.details = self.GetCertDetails()
        if not self.is_valid:
            return None

        # Get original issue and expriation timestamps
        self.issued_timestamp = round(mktime(strptime(self.details['notBefore'], "%b %d %H:%M:%S %Y %Z")));
        self.expiration_timestamp = round(mktime(strptime(self.details['notAfter'], "%b %d %H:%M:%S %Y %Z")));

        # Adjust for local timezone setting
        local_timezone_offset = timezone if localtime().tm_isdst == 0 else altzone
        current_timestamp = round(time()) + local_timezone_offset

        # Do math to determine days, hour, seconds remaining until expiration
        self.seconds_until_expiration = self.expiration_timestamp - current_timestamp
        self.hours_until_expiration = ceil(self.seconds_until_expiration / 3600)
        self.days_until_expiration =  self.hours_until_expiration // 24


    def GetCertDetails(self):

        context = create_default_context()

        # Verify hostname is resolvable
        try:
            gethostbyname(self.hostname)
        except:
            return False, "does not resolve in DNS"

        # Verify hostname is reachable on port 443
        try:
            sock = create_connection((self.hostname, "443"), timeout=2)
        except:
            return False, "is not reachable on port 443"

        # Attempt SSL connection
        try:
            ssock = context.wrap_socket(sock, server_hostname = self.hostname)
        except:
            return False, "SSL handshake failed - hostname mismatch, bad chain, or expired certificate?"

        # Attempt to get certificate details
        try:
            cert_details = ssock.getpeercert()
        except:
            return False, "Cannot get certificate details"

        # Cert looks good
        return True, cert_details


def get_targets(input_file: str) -> list:

    targets = []
    try:
        f = open(input_file, 'r')
    except:
        exit("Can't open file: '"+ input_file +"'")

    for line in f:
        if line.startswith('#') or line.startswith('\n'):
            continue
        else:
            targets .append(line.rstrip())
    f.close()
    return targets


def main():

    if len(argv) < 2:
        exit("Usage: " + argv[0] + " 'hostnames_file'")
    input_file = argv[1]
    recipient = None
    if len(argv) > 2:
        recipient = argv[2]
    if len(argv) > 3:
        sender = argv[3]
    else:
        sender = getuser() + "@" + getaddrinfo(gethostname(), 0, flags=AI_CANONNAME)[0][3]

    hostnames = get_targets(input_file)

    output = ""
    for hostname in hostnames:

        cert = SSLCert(hostname)

        if not cert.is_valid:
            output += "Problem for " + hostname + ": " + cert.details + "\n"
            continue

        if cert.days_until_expiration <= DAYS_THRESHOLD:
            output += cert.hostname + " will expire in "
            if cert.days_until_expiration <= 1:
                output += str(cert.hours_until_expiration) + " hours!!!\n"
            else:
                output += str(cert.days_until_expiration) + " days\n"

    if recipient and output:
        subject = "An SSL certificate is expiring soon!"
        message = f"From: {sender}\nTo: {recipient}\nSubject: {subject}\n{output}"
        try:
            server = SMTP('localhost', port=25)
            server.ehlo()
            server.sendmail(sender, recipient, message)
            server.quit()
        except Exception as e:
            print(e)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
