#!/usr/bin/env python3

import google.auth
from traceback import format_exc
from platform import system
from os import environ
from collections import deque, Counter
from random import choices
from gcp_network import *
from file_functions import *
from time import time
#from guppy import hpy


FIELDS = ('instances', 'networks', 'subnets', 'addresses', 'routes', 'forwarding_rules', 'cloud_routers',
          'routes', 'ssl_certs', 'peerings', 'vpn_tunnels', 'interconnects')


def get_network_data(resource_object, project_id: str) -> dict:

    data = {}
    for field in FIELDS:
        data[field] = []

    try:
        data['networks'], data['peerings'] = get_networks(resource_object, project_id)
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


def main():


    """
    # verify we have a valid token
    print("Checking for valid auth credential..", end='')
    creds, project_id = google.auth.default()
    if google.auth.default():
        print("OK!")
    else:
        quit("Not logged in; run 'gcloud auth application-default login'")
    """

    start_time = time()
    split = start_time

    print("Connecting to Google Compute API..", end='')
    try:

        resource_object = connect_to_api("compute", "v1")

        print("OK!")
        network_data = {}
        for field in FIELDS:
            network_data[field] = deque()

        print("Getting a list of Projects..", end='')
        project_ids = get_project_ids()
        print("OK!")
        print(project_ids)

        print(f"Getting network data for: {len(project_ids)} Project IDs.", end='')
        for PROJECT_ID in project_ids:
            print(f".", end='')
            project_data = get_network_data(resource_object, PROJECT_ID)
            for field in FIELDS:
                network_data[field].extend(project_data.get(field, []))
        print("Done!")

        print("seconds_to_execute_api_calls:", round((time() - split), 3))

        #h = hpy()
        #print(h.heap())

        #network_data['quota_counts'] = []
        counts = {}
        count_fields = {
            'projects': {},
            'networks': ('addresses', 'instances', 'forwarding_rules'),
            #'region': {},
        }
        for sheet in count_fields.keys():
            counts[sheet] = {}

        #counters = {'networks': {}, 'subnet_name': {}, 'forwarding_rules': {}}
        #count_fields = ('addresses', 'instances', 'forwarding_rules')
        for sheet, count_fields in count_fields.items():
            for field in count_fields:
                counts[sheet][field] = Counter([row.get('network_name') for row in network_data.get(field, [])])
            counts[sheet]['internal_tcp_udp_fwd_rules'] = Counter([row.get('network_name') if row['lb_scheme'] == "INTERNAL" else None for row in network_data.get('forwarding_rules', [])])
            counts[sheet]['internal_managed_fwd_rules'] = Counter([row.get('network_name') if row['lb_scheme'] == "INTERNAL_MANAGED" else None for row in network_data.get('forwarding_rules', [])])
            #counts[sheet]['something'] = 69

        counter_sheets = {}
        counter_sheets['networks'] = []
        for network in network_data['networks']:
            network_name = network['name']
            _ = {
                'network_name': network_name,
                'project_id': network['project_id'],
            }
            for field in count_fields:
                _[field] = counts['networks'][field].get(network_name, 0)
            _['internal_tcp_udp_fwd_rules'] = counts['networks']['internal_tcp_udp_fwd_rules'].get(network_name, 0)
            _['internal_managed_fwd_rules'] = counts['networks']['internal_managed_fwd_rules'].get(network_name, 0)
            counter_sheets['networks'].append(_)

        """
        counter_sheets = {
            'networks': "network_name",
            'subnets': "subnet_name",
            #'forwarding_rules': "else",
        }
        #counts = {'networks': {}, 'subnet_name': {}, 'forwarding_rules': {}}
        count_fields = ('addresses', 'instances', 'forwarding_rules')
        for sheet_name, field_name in counter_sheets.items():
            #counts[sheet_name] = {}
            for field in count_fields:
                #counts[sheet_name][field] = Counter([i.get(field_name) for i in network_data.get(field, [])])
                #counts[sheet_name]['internal_tcp_udp_forwarding_rules'] = Counter([i.get(field_name) for i in network_data.get(field, [])])
                #print(counts[sheet_name][field])
            for key, value in counts[sheet_name][field].items():
                if not key:  # Skip ones where key is None
                    continue
                #print(sheet_name, key, field, value)
                row = {'name': key}
                for field in count_fields:
                    row[field] = counts[sheet_name][field][key]
                network_data[sheet_name].append(row)
        """

        print("seconds_to_execute_counting:", round((time() - split), 3))
        split = time()

        print("seconds_to_execute_sorting:", round((time() - split), 3))

        # Write network data to Excel File
        wb_data = {}
        for field in FIELDS:
            wb_data[field] = list(network_data[field])
        network_data.clear()
        for sheet_name, data in counter_sheets.items():
            wb_data[sheet_name + "_counts"] = data
        output_file = f"{get_home_dir()}network_data.xlsx"
        write_to_excel(wb_data, output_file)
        print(f"Wrote data to file: {output_file}")
        print("seconds_to_execute_write:", round((time() - split), 3))

    except Exception as e:

        print(str(format_exc()))


if __name__ == "__main__":

    main()

