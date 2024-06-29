import ssl, socket

SERVER_HOSTNAME = "www.j5.org"

try:
    sock = socket.create_connection((SERVER_HOSTNAME, 443), timeout=1)
    ssl_context = ssl.create_default_context()
    ssock = ssl_context.wrap_socket(sock, server_hostname=SERVER_HOSTNAME)
    tls_info = {
        'version': ssock.version(),
         'cert_details': ssock.getpeercert(),
    }
except Exception as e:
    quit(e)

print(tls_info)
