
# Python Scripts

Just a random collection of some Python scripts I've written

## reverse_dns_scan

Shows the reverse DNS entries for a given IP range. Usage example:

```
./reverse_dns_scan.py 192.168.1.0/24
```

## check_ssl

Shows information about the SSL handshake and certificate of a certain site.  Usage example:

```
./check_ssl.py www.google.com
```

## site_checker

Sends an HTTP/HTTPS request to multiple sites and displays HTTPS status code and SSL/TLS handshake info

### Usage Instructions

Create a list of hostnames to hit

```
whamola.net
icompare.shop
primus.j5.org:80
```

Run script with this file as the first parameter

```
./site_checker.py hostnames.txt
```

To enable e-mail notification, set a 2nd parameter. The "from" addresses can be the third paremter

```
./site_checker.py hostnames.txt me@mydomain.com nobody@nowhere.net
```
