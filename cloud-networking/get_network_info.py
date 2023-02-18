#!/usr/bin/env python3

import google.auth
import ipaddress
import traceback
import asyncio
import platform
import os
import sys
from gcp_network import *
from file_functions import *
from collections import deque


from time import time
from guppy import hpy

#PROJECT_IDS = ["otl-ems-netops", "otl-vpc-shared", "otl-vpc-shared-pre-comm", "otl-core-network-pre-comm"]

FIELDS = ('instances', 'networks', 'subnets', 'addresses', 'load_balancers', 'cloud_routers', 'routes', 'ssl_certs')



if __name__ == "__main__":

    # verify we have a valid token
    creds, project_id = google.auth.default()
    if not google.auth.default():
        quit("Not logged in; run 'gcloud auth application-default login'")

    start_time: time = time()

    try:

        resource_object = connect_to_api()

        network_data = {}
        for field in FIELDS:
            network_data[field] = deque()

        print(f"Getting network data for the following Project IDs:")
        for PROJECT_ID in get_project_ids():
            print(f"  - {PROJECT_ID}...")
            #network_data.extend(get_network_data(resource_object, PROJECT_ID))
            network_data['addresses'].extend(get_addresses(resource_object, PROJECT_ID))
            #network_data['load_balancers'].extend(get_forwarding_rules(resource_object, PROJECT_ID))
            network_data['instances'].extend(get_instances(resource_object, PROJECT_ID))
            network_data['ssl_certs'].extend(get_ssl_certs(resource_object, PROJECT_ID))
            network_data['cloud_routers'].extend(get_cloud_routers(resource_object, PROJECT_ID))
            #cloud_router_names = [ router.get('name') for router in network_data['cloud_routers']]
            #    network_data['routes'].extend(get_cloud_router_routes(resource_object, PROJECT_ID))

        print("Done!")

        print("seconds_to_execute:", round((time() - start_time), 3))
        h = hpy()
        print(h.heap())

        wb_data = {}
        for field in FIELDS:
            wb_data[field] = list(network_data[field])

        #print(wb_data)
        network_data.clear()

        if platform.system().lower().startswith("win"):
            home_dir = os.environ.get("USERPROFILE")
        else:
            home_dir = os.environ.get("HOME")
        output_file = f"{home_dir}/network_data.xlsx"
        write_to_excel(wb_data, output_file)

    except Exception as e:

        print(str(traceback.format_exc()))

