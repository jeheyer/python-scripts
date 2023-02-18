
A basic Python script to check sites for availability and SSL certs

# Instructions

Create a text file listing hostnames to check.  By default, port is 443

```
whamola.net
icompare.shop
primus.j5.org:80
```

Run script with this file as the first parameter

```
./site_checker.py hostnames.txt
```

# Optional parameters

To enable e-mail notification, set a 2nd parameter. The "from" addresses can be the third paremter

```
./site_checker.py hostnames.txt me@mydomain.com nobody@nowhere.net
```
