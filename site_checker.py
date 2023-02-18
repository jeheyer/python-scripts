#!/usr/bin/env python3

def BuildTable(column_names, rows):

    from prettytable import PrettyTable
 
    t = PrettyTable()
    t.field_names = column_names
    for row in rows:
        t.add_row(row)
    return t

class Target:

    def __init__(self, target, port = 443):

        if ":" in target:
            self.hostname, self.port = target.split(":")
        else:
            self.hostname = target
            self.port = port

        self.is_resolvable = False
        self.is_reachable = False        
        self.CheckReachability()

        self.tls_info = None
        self.CheckSSL()
        self.CalcSSLExpiration()

        self.http_status = None
        self.CheckHTTP()

    def CheckReachability(self):
        
        import socket

        # Verify hostname resolves in DNS
        try:
            self.ip_address = socket.gethostbyname(self.hostname)
            self.is_resolvable = True
        except:
            self.is_resolvable = False
            self.ip_address = None

        if self.is_resolvable:
            # Verify hostname is reachable on port
            try:
                self.sock = socket.create_connection((self.hostname, str(self.port)), timeout=1)
                self.is_reachable = True
            except:
                self.is_reachable = False
    
    def CheckSSL(self):

        import ssl, time

        if self.is_reachable and self.port == 443:
            # Perform SSL/TLS handshake
            try:
                self.ssl_context = ssl.create_default_context()
                ssock = self.ssl_context.wrap_socket(self.sock, server_hostname=self.hostname)
                self.tls_info = ssock.version()
                self.cert_details = ssock.getpeercert()
                self.cert_issued_timestamp = round(time.mktime(time.strptime(self.cert_details['notBefore'], "%b %d %H:%M:%S %Y %Z")))
                self.cert_expiration_timestamp = round(time.mktime(time.strptime(self.cert_details['notAfter'], "%b %d %H:%M:%S %Y %Z")))
            except:
                self.tls_info = "ERROR"
                self.cert_details = None
        else:
            self.tls_info = None
            self.cert_details = None
        
    def CheckHTTP(self):

        import http.client
    
        if self.is_reachable:
            try:
                if self.port == 443:
                    conn = http.client.HTTPSConnection(self.hostname, self.port, timeout=1, context=self.ssl_context)
                else:
                    conn = http.client.HTTPConnection(self.hostname, self.port, timeout=1)
                conn.request(method="GET", url="/", headers={'User-agent':"Python http.client"})
                resp = conn.getresponse()
                self.http_status = str(resp.status)
                if resp.reason:
                    self.http_status += ' ' + str(resp.reason)
            except:
                self.http_status = None
            conn.close()
    
    def CalcSSLExpiration(self):

        import time, math

        if self.tls_info and self.cert_details:

            # Get original issue and expriation timestamps
            self.issued_timestamp = round(time.mktime(time.strptime(self.cert_details['notBefore'], "%b %d %H:%M:%S %Y %Z")))
            self.expiration_timestamp = round(time.mktime(time.strptime(self.cert_details['notAfter'], "%b %d %H:%M:%S %Y %Z")))
            self.expiration_datetime = self.cert_details['notAfter']

            # Adjust for local timezone setting
            local_timezone_offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
            current_timestamp = round(time.time()) + local_timezone_offset

            # Do math to determine days, hour, seconds remaining until expiration
            self.seconds_until_expiration = self.expiration_timestamp - current_timestamp
            self.hours_until_expiration = math.ceil(self.seconds_until_expiration / 3600)
            self.days_until_expiration =  self.hours_until_expiration // 24
        else:
            self.issued_timestamp = None
            self.expiration_timestamp = None

def ReadHostnamesList(input_file):

    import sys

    hostnames = []
    try:
        f = open(input_file, 'r')
    except:
        sys.exit("Can't open file: '"+ input_file +"'")

    for line in f:
        if line.startswith('#') or line.startswith('\n'):
            continue
        else:
            hostnames.append(line.rstrip())
    f.close()
    return hostnames

def main():

    import sys, socket, getpass, smtplib

    DAYS_THRESHOLD = 30

    if len(sys.argv) < 2:
        sys.exit("Usage: " + sys.argv[0] + " 'hostnames_file'")
    input_file = sys.argv[1]
    recipient = None
    if len(sys.argv) > 2:
        recipient = sys.argv[2]
    if len(sys.argv) > 3:
        sender = sys.argv[3]
    else:
        sender = getpass.getuser() + "@" + socket.getaddrinfo(socket.gethostname(), 0, flags=socket.AI_CANONNAME)[0][3]

    hostnames = ReadHostnamesList(input_file)

    output = ""
    results = []
    for hostname in hostnames:

        target = Target(hostname)
        #print(target.hostname, target.port, target.tls_info, target.http_status)
        notes = ""
        if target.tls_info:
            if target.tls_info == "ERROR":
                notes += "SSL Handshake failure"
            else:
                if target.tls_info != "TLSv1.3" and target.tls_info != "TLSv1.2":
                    notes += "Does not support TLS 1.2 or 1.3"
        if target.cert_details:
            if target.days_until_expiration <= DAYS_THRESHOLD:
                if target.days_until_expiration <= 2:
                    notes += f"Cert expires in {target.hours_until_expiration} hours!!!"
                else:
                    notes += f"Cert expires in {target.days_until_expiration} days"
        if target.http_status:
            if 500 <= int(target.http_status[:3]) < 600:
                 notes += "HTTP 5xx response"
        results.append([target.hostname + ":" + str(target.port), target.ip_address, target.tls_info, target.http_status, notes])

    output = BuildTable(["Target", "IP Address", "TLS info", "HTTP Status", "Notes"], results)

    if recipient and notes:
        subject = "Site Issue"
        message = f"From: {sender}\nTo: {recipient}\nSubject: {subject}\n{output}"
        try:
            server = smtplib.SMTP('localhost', port=25)
            server.ehlo()
            server.sendmail(sender, recipient, message)
            server.quit()
        except Exception as e:
            print(e)
    else:
        print(output)

if __name__ == "__main__":

    from time import time

    start_time: time = time()
    main()
    print("seconds_to_execute:", round((time() - start_time), 3))

