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
from collections import deque, Counter
from random import choices
from time import time
#from guppy import hpy


FIELDS = ('instances', 'networks', 'subnets', 'addresses', 'routes', 'forwarding_rules', 'cloud_routers',
          'routes', 'ssl_certs', 'vpn_tunnels', 'interconnects')


def get_network_data(resource_object, project_id: str) -> dict:

    data = {}
    for field in FIELDS:
        data[field] = []

    try:
        data['addresses'] = get_addresses(resource_object, project_id)
        data['routes'] = get_routes(resource_object, project_id)
        data['forwarding_rules'] = get_forwarding_rules(resource_object, project_id)
        data['instances'] = get_instances(resource_object, project_id)
        data['ssl_certs'] = get_ssl_certs(resource_object, project_id)
        data['cloud_routers'] = get_cloud_routers(resource_object, project_id)
        data['vpn_tunnels'] = get_vpn_tunnels(resource_object, project_id)
        data['interconnects'] = get_interconnects(resource_object, project_id)
    except Exception as e:
        raise e

    return data


async def main():

    # verify we have a valid token
    creds, project_id = google.auth.default()
    if not google.auth.default():
        quit("Not logged in; run 'gcloud auth application-default login'")

    start_time = time()
    split = start_time

    try:

        resource_object = connect_to_api()

        network_data = {}
        for field in FIELDS:
            network_data[field] = deque()

        project_ids = get_project_ids()
        #project_ids = choices(project_ids, k=10)
        #project_ids = ["websites-270319"]
        #project_ids = ("otl-ems-netops", "otl-vpc-shared", "otl-core-network-pre-comm", "otl-vpc-shared-pre-comm")

        print(f"Getting network data for ${len(project_ids)} Project IDs:")
        tasks = set()
        for PROJECT_ID in project_ids:
            print(f".", end='')
            #task = asyncio.create_task(get_network_data(resource_object, PROJECT_ID))
            #tasks.add(task)
            #await task
            project_data = get_network_data(resource_object, PROJECT_ID)
            #task.add_done_callback(tasks.discard)
            for field in FIELDS:
                network_data[field].extend(project_data[field])
        print("Done!")

        print("seconds_to_execute_api_calls:", round((time() - split), 3))
        split = time()
        #h = hpy()
        #print(h.heap())

        counter_sheets = {
            'networks': "network_name",
            'subnets': "subnet_name",
            #'load_balancers': "else",
        }
        counts = {}
        count_fields = ('addresses', 'instances', 'forwarding_rules')
        for sheet_name, field_name in counter_sheets.items():
            counts[sheet_name] = {}
            for field in count_fields:
                counts[sheet_name][field] = Counter([i.get(field_name) for i in network_data.get(field, [])])
                #print(counts[sheet_name][field])
            for key, value in counts[sheet_name][field].items():
                if not key:  # Skip ones where key is None
                    continue
                #print(sheet_name, key, field, value)
                row = {'name': key}
                for field in count_fields:
                    row[field] = counts[sheet_name][field][key]
                network_data[sheet_name].append(row)

        print("seconds_to_execute_counting:", round((time() - split), 3))
        split = time()

        print("seconds_to_execute_sorting:", round((time() - split), 3))

        wb_data = {}
        for field in FIELDS:
            wb_data[field] = list(network_data[field])

        network_data.clear()

        my_os = platform.system().lower()
        if my_os.startswith("win"):
            home_dir = os.environ.get("USERPROFILE")
            seperator = "\\"
        elif my_os:
            home_dir = os.environ.get("HOME")
            seperator = "/"
        output_file = f"{home_dir}{seperator}network_data.xlsx"
        write_to_excel(wb_data, output_file)
        print(f"Wrote data to file: {output_file}")
        print("seconds_to_execute_write:", round((time() - split), 3))

    except Exception as e:

        print(str(traceback.format_exc()))


if __name__ == "__main__":

    asyncio.run(main())