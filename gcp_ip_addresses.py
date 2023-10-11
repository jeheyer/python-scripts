#!/usr/bin/env python3 

from asyncio import run, gather, create_task
from aiohttp import ClientSession
from google.auth import default
from google.auth.transport.requests import Request
from ipaddress import ip_address
import csv

CSV_FILE = 'gcp_ip_addresses.csv'


async def make_gcp_call(api_name: str, method: str, access_token: str) -> list:

    method = method[1:] if method.startswith('/') else method
    url = f'https://{api_name}.googleapis.com/{method}'
    suffix = url.split('/')[-1]
    key = 'items' if api_name in ['compute', 'sqladmin'] else suffix

    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {}
        results = []
        async with ClientSession(raise_for_status=True) as session:
            while True:
                async with session.get(url, headers=headers, params=params, timeout=20) as response:
                    if int(response.status) == 200:
                        json = await response.json()
                        if 'aggregated/' in method:
                            items = json.get(key, {})
                            for k, v in items.items():
                                results.extend(v.get(suffix, []))
                        else:
                            results.extend(json.get(key, []))
                        if page_token := json.get('nextPageToken'):
                            params.update({'pageToken': page_token})
                        else:
                            break
                    else:
                        raise response
        return results
    except:
        await session.close()
        return []

    return results


async def get_project_ids(access_token: str) -> list:

    try:
        api_name = 'cloudresourcemanager'
        method = '/v1/projects'
        projects = await make_gcp_call(api_name, method, access_token)
        return [p['projectId'] for p in projects]
    except Exception as e:
        raise e


async def get_instance_nics(project_id: str, access_token: str) -> list:

    try:
        api_name = 'compute'
        method = f'/compute/v1/projects/{project_id}/aggregated/instances'
        items = await make_gcp_call(api_name, method, access_token)
    except:
        return []

    results = []
    for item in items:
        for nic in item.get('networkInterfaces', []):
            if network := nic.get('network'):
                network_name = network.split('/')[-1]
                network_project_id = network.split('/')[-4]
                zone = item.get('zone', 'null/unknown-0')
                region = zone.split('/')[-1][:-2]
                result = {
                    'ip_address': nic.get('networkIP'),
                    'type': 'GCE Instance NIC',
                    'name': item['name'],
                    'project_id': project_id,
                    'network_id': f'{network_project_id}/{network_name}',
                    'region': region,
                }
                results.append(result)
                # Also check if the NIC has any NAT IPs
                if access_configs := nic.get('accessConfigs'):
                    for access_config in access_configs:
                        if nat_ip := access_config.get('natIP'):
                            result['ip_address'] = nat_ip
                            result['type'] = 'GCE Instance NAT IP'
                            result['name'] = access_config['name']
                            result['network_id'] = 'n/a'
                            results.append(result)

    return results


async def get_fwd_rules(project_id: str, access_token: str) -> list:

    try:
        api_name = 'compute'
        methods = [
            f'/compute/v1/projects/{project_id}/aggregated/forwardingRules',
            f'/compute/v1/projects/{project_id}/global/forwardingRules',
        ]
        items = []
        for method in methods:
            items.extend(await make_gcp_call(api_name, method, access_token))
    except:
        return []

    results = []
    for item in items:
        if network := item.get('network'):
            network_project_id = network.split('/')[-4]
            network_name = network.split('/')[-1]
            network_id = f'{network_project_id}/{network_name}'
        else:
            network_id = 'n/a'
        if region := item.get('region'):
            region = region.split('/')[-1]
        else:
            region = 'global'
        result = {
            'ip_address': item.get('IPAddress'),
            'type': "Forwarding Rule",
            'name': item['name'],
            'project_id': project_id,
            'network_id': network_id,
            'region': region,
        }
        results.append(result)

    return results




async def get_gke_endpoints(project_id: str, access_token: str) -> list:

    try:
        api_name = 'container'
        method = f'/v1/projects/{project_id}/locations/-/clusters'
        clusters = await make_gcp_call(api_name, method, access_token)
    except:
        return []

    results = []
    for cluster in clusters:
        endpoint_ips = []
        network_id = 'n/a'
        if private_cluster_config := cluster.get('privateClusterConfig'):
            if private_cluster_config.get('enablePrivateEndpoint'):
                endpoint_ips.append(private_cluster_config.get('privateEndpoint'))
                if node_pools := cluster.get('nodePools'):
                    if network_config := node_pools[0].get('networkConfig'):
                        if network := network_config.get('network'):
                            network_project_id = network.split('/')[-4]
                            network_name = network.split('/')[-1]
                            network_id = f'{network_project_id}/{network_name}'
            else:
                endpoint_ips.append(private_cluster_config.get('publicEndpoint'))
        location = cluster.get('location', 'unknown-0')
        region = location.split('/')[-1][:-2] if location[-2] == '-' else location
        for endpoint_ip in endpoint_ips:
            results.append({
                'ip_address': endpoint_ip,
                'type': 'GKE Endpoint',
                'name': cluster['name'],
                'project_id': project_id,
                'network_id': network_id,
                'region': region,
                #'pods_range': cluster.get('clusterIpv4Cidr'),
                #'services_range': cluster.get('servicesIpv4Cidr'),
                #'masters_range': cluster['privateClusterConfig']['masterIpv4CidrBlock'] if 'privateClusterConfig' in cluster else None,
            })

    return results


async def get_cloudsql_instances(project_id: str, access_token: str) -> list:

    try:
        api_name = 'sqladmin'
        method = f'/v1/projects/{project_id}/instances'
        items = await make_gcp_call(api_name, method, access_token)
    except:
        return []

    results = []
    for item in items:
        if ip_configuration := item['settings'].get('ipConfiguration'):
            if network := ip_configuration.get('privateNetwork'):
                network_project_id = network.split('/')[-4]
                network_name = network.split('/')[-1]
                network_id = f'{network_project_id}/{network_name}'
            else:
                network_id = 'n/a'
        for address in item.get('ipAddresses', []):
            result = {
                'ip_address': address.get('ipAddress'),
                'type': 'Cloud SQL Instance',
                'name': item['name'],
                'project_id': project_id,
                'network_id': network_id,
                'region': item.get('region', 'unknown'),
            }
            results.append(result)

    return results

async def main():

    try:
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        credentials, project_id = default(scopes=scopes)
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
    try:
        for _ in await gather(*tasks):
            ip_addresses.extend(_)
    except Exception as e:
        quit(e)

    return ip_addresses

if __name__ == '__main__':

    _ = run(main())
    data = sorted(_, key=lambda x: ip_address(x['ip_address']), reverse=False)
    print(data)
    try:
        csvfile = open(CSV_FILE, 'w', newline='')
        writer = csv.writer(csvfile)
        writer.writerow(data[0].keys())
        [writer.writerow(row.values()) for row in data]
        csvfile.close()
        print(f"Wrote results to file '{CSV_FILE}'!")
    except Exception as e:
        quit(e)
