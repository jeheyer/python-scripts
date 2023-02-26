#!/usr/bin/env python3

from sys import argv, exit
from socket import gethostbyaddr 
from ipaddress import ip_network


def get_reverse_dns(hostname):

    try:
        return gethostbyaddr(host)[0][0:64]
    except:
        return None


if len(argv) > 1:
    network = argv[1]
else:
    exit(f"Must provide subnet as parameter.  Example: {argv[0]} 192.168.1.0/24")

network_addr, mask = network.split('/')
power = 32 - int(mask)

hosts = list(ip_network(network).subnets(power))

for host in hosts:
    host = str(host).split('/')[0]
    name = get_reverse_dns(host)
    if name:
        print(f"{host}: {name}")
