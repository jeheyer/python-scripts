#!/usr/bin/env python3 

from asyncio import run, gather, create_task
from collections import Counter
from google.auth import default
from google.auth.transport.requests import Request
from gcp_functions import make_gcp_call
import csv

CSV_FILE = 'gcp_ip_addresses.csv'


async def get_project_ids(access_token: str) -> list:

    url = "https://cloudresourcemanager.googleapis.com/v1/projects"
    try:
        projects = await make_gcp_call(url, access_token, key='projects')
        return [p['projectId'] for p in projects]
    except Exception as e:
        raise e


async def get_instance_nics(project_id: str, access_token: str) -> list:

    results = []

    try:
        url = f"compute/v1/projects/{project_id}/aggregated/instances"
        items = await make_gcp_call(url, access_token)
    except:
        return []

    for item in items:
        for nic in item.get('networkInterfaces', []):
            if network := nic.get('network'):
                network_name = network.split('/')[-1]
                network_project_id = network.split('/')[-4]
                zone = item.get('zone', 'null/unknown-0')
                result = {
                    'ip_address': nic.get('networkIP'),
                    'type': "GCE Instance NIC",
                    'name': item['name'],
                    'project_id': project_id,
                    'network_id': f"{network_project_id}/{network_name}",
                    'region': zone.split('/')[-1][:-2],
                }
                results.append(result)
                # Also check if the instance has any active NAT IP addresses
                if access_configs := nic.get('accessConfigs'):
                    for access_config in access_configs:
                        if ip_address := access_config.get('natIP'):
                            result['ip_address'] = ip_address
                            result['type'] = "GCE Instance NAT IP"
                            result['name'] = access_config['name']
                            result['network_id'] = "n/a"
                            results.append(result)

    return results


async def get_fwd_rules(project_id: str, access_token: str) -> list:

    urls = [
        f"compute/v1/projects/{project_id}/aggregated/forwardingRules",
        f"compute/v1/projects/{project_id}/global/forwardingRules",
    ]
    results = []

    try:
        items = []
        for url in urls:
            items.extend(await make_gcp_call(url, access_token))
    except:
        return []

    for item in items:
        result = {
            'ip_address': item.get('IPAddress'),
            'type': "Forwarding Rule",
            'name': item['name'],
            'project_id': project_id,
            'network_id': "n/a",
            'region': item.get('region', 'global-0').split('/')[-1],
        }
        if network := item.get('network'):
            network_project_id = network.split('/')[-4]
            network_name = network.split('/')[-1]
            result['network_id'] = f"{network_project_id}/{network_name}"
        results.append(result)

    return results


async def get_cloudsql_instances(project_id: str, access_token: str) -> list:

    url = f"https://sqladmin.googleapis.com/v1/projects/{project_id}/instances"
    results = []

    try:
        items = await make_gcp_call(url, access_token)
    except:
        return []

    for item in items:
        network_project_id = "unknown"
        network_name = "unknown"
        if ip_configuration := item['settings'].get('ipConfiguration'):
            if network := ip_configuration.get('privateNetwork'):
                network_project_id = network.split('/')[-4]
                network_name = network.split('/')[-1]
        for address in item.get('ipAddresses', []):
            result = {
                'ip_address': address.get('ipAddress'),
                'type': "Cloud SQL Instance",
                'name': item['name'],
                'project_id': project_id,
                'network_id': f"{network_project_id}/{network_name}",
                'region': item.get('region', 'unknown'),
            }
            results.append(result)

    return results


async def get_gke_endpoints(project_id: str, access_token: str) -> list:

    url = f"https://container.googleapis.com/v1/projects/{project_id}/locations/-/clusters"
    results = []

    try:
        clusters = await make_gcp_call(url, access_token, key='clusters')
        for cluster in clusters:
            network_project_id = "unknown"
            network_name = "unknown"
            endpoint_ips = []
            if private_cluster_config := cluster.get('privateClusterConfig'):
                endpoint_ips.append(private_cluster_config.get('publicEndpoint'))
                if private_cluster_config.get('enablePrivateEndpoint'):
                    endpoint_ips.append(private_cluster_config.get('privateEndpoint'))
            if node_pools := cluster.get('nodePools'):
                if network_config := node_pools[0].get('networkConfig'):
                    if network := network_config('network'):
                        network_project_id = network.split('/')[-4]
                        network_name = network.split('/')[-1]
            location = cluster.get('location', 'unknown-0')
            for endpoint_ip in endpoint_ips:
                results.append({
                    'ip_address': endpoint_ip,
                    'type': "GKE Endpoint",
                    'name': cluster['name'],
                    'project_id': project_id,
                    'network_id': f"{network_project_id}/{network_name}",
                    'region': location.split('/')[-1][:-2] if location[-2] == '-' else location,
                    #'pods_range': cluster.get('clusterIpv4Cidr'),
                    #'services_range': cluster.get('servicesIpv4Cidr'),
                    #'masters_range': cluster['privateClusterConfig']['masterIpv4CidrBlock'] if 'privateClusterConfig' in cluster else None,
                })
    except:
        return []

    return results


async def main():

    try:
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        credentials, project_id = default(scopes=scopes, quota_project_id=None)
        credentials.refresh(Request())
        access_token = credentials.token
        project_ids = await get_project_ids(access_token)
    except Exception as e:
        quit(e)

    tasks = []
    for project_id in project_ids:
        tasks.append(create_task(get_instance_nics(project_id, access_token)))
        tasks.append(create_task(get_fwd_rules(project_id, access_token)))
        tasks.append(create_task(get_cloudsql_instances(project_id, access_token)))
        tasks.append(create_task(get_gke_endpoints(project_id, access_token)))

    ip_addresses = []
    for _ in await gather(*tasks):
        ip_addresses.extend(_)

    return ip_addresses

if __name__ == "__main__":

    _ = run(main())
    ip_addresses = sorted(_, key=lambda x: x['ip_address'], reverse=False)

    #print(ip_addresses)


    csvfile = open(CSV_FILE, 'w', newline='')
    writer = csv.writer(csvfile)
    writer.writerow(ip_addresses[0].keys())
    [writer.writerow(ip_address.values()) for ip_address in ip_addresses]
    csvfile.close()
