#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from squid_log_viewer import get_squid_data

def main():

    from time import time
    from random import sample
    from math import floor
    from datetime import datetime
    from guppy import hpy

    start_time: time = time()
    options = {'location': "GCP"}
    data = get_squid_data(options)
    print("seconds_to_execute:", round((time() - start_time), 3))
    print(data['hits_by_host'], data['requests_by_client_ip'], data['hits_by_status_code'], data['bytes_by_client_ip'])
    if len(data['entries']) > 0:
        print(f"now: {floor(start_time)}\n first = {data['entries'][0]}\n last = {data['entries'][-1]}")
        random_samples = sample(data['entries'],3)
        for _ in range(len(random_samples)):
            print(f" random sample {_}: {random_samples[_]}")
    h = hpy()
    print(h.heap())

if __name__ == '__main__':
    main()

