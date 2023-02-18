from datetime import datetime
from gcp_api import *


def get_ssl_certs(resource_object, project_id: str) -> list:

    ssl_certs = []

    # Global
    try:
        _ = resource_object.sslCertificates().list(project=project_id).execute()
        items = _.get('items', [])
    except Exception as e:
        items = []

    for item in items:
        #print(item)
        info = {
           'name': item.get('name'),
           'description': item.get('description'),
           'type': item.get('type', "UNKNOWN"),
        }
        if 'expireTime' in item:
           expire_ymd = item['expireTime'][:10] # Read Year, Monday, Day from expireTime field
           info['expires_date'] = expire_ymd
           info['expires_timestamp'] = datetime.timestamp(datetime.strptime(expire_ymd, "%Y-%m-%d"))
        ssl_certs.append(info)

    # Regional

    return ssl_certs


def get_sharedvpc_service_projects(resource_object, project_id: str) -> list:

    _ = resource_object.projects().getXpnResources(project=project_id).execute()
    return [p['id'] for p in _.get('resources', [])]


def get_sharedvpc_host_projects(resource_object, project_id: str) -> list:

    _ = resource_object.projects().listXpnHosts(project=project_id, body={}).execute()
    return [p['name'] for p in _.get('items', []) ]


def get_routes(resource_object, project_id: str) -> {}:

    """
    Get list of all routes, project level
    """

    routes_per_network = {}

    page_token = None
    while True:
        _ = resource_object.routes().list(project=project_id, pageToken=page_token).execute()
        items = _.get('items', [])
        page_token = _.get('nextPageToken')
        for route in items:
            #print(route)
            network_name = route['network'].split('/')[-1]
            if not network_name in routes_per_network:
                routes_per_network[network_name] = []
            routes_per_network[network_name].append(route)

        # Check for a next page token in the response; if one isn't present, we're done
        if not page_token:
            break

    return routes_per_network


def get_cloud_routers(resource_object, project_id: str, region: str = None) -> list:

    cloud_routers = []

    try:
        _ = resource_object.routers().aggregatedList(project=project_id).execute()
        items = _.get('items',{})
    except Exception as e:
        items = {}

    for item in parse_aggregated_results(items, 'routers'):
        info = {
            'network_name': item.get('network').split('/')[-1],
            'region': item.get('region').split('/')[-1],
            'num_interfaces': len(item.get('interfaces', [])),
        }
        cloud_routers.append(info)

    return cloud_routers


def get_cloud_router_routes(resource_object, project_id: str, cloud_router_name: str, region_name: str) -> list:

    """
    Get full list of routes from a given cloud router
    """

    routes = []

    _ = resource_object.routers().getRouterStatus(project=project_id,region=region_name,router=cloud_router_name).execute()
    best_routes = _['result'].get('bestRoutes', [])

    for item in best_routes:
        info = {
            'destRange': item['destRange'],
            'network': item['network'].split('/')[-1],
            'cloud_router': cloud_router_name,
            'region': item.get('region'),
            'nextHopIp': item.get('nextHopIp'),
            'priority': item.get('priority', 1000),
            'asPaths': item.get('asPaths', [])[0]['asLists']
        }
        routes.append(info)

    return routes


def get_cloud_nats(resource_object, project_id: str, cloud_routers: dict) -> list:

    for router_name, region_name in cloud_routers.items():
        _ = resource_object.routers().getRouterStatus(project=project_id, region=region_name, router=router_name).execute()
        if 'natStatus' in _.get('result', []):
            for _ in _['result'].items():
                if _[0] == 'natStatus':
                    info =_[1][0]
                    if info['minExtraNatIpsNeeded'] > 0:
                        print(f"Name: {info['name']}, IPs: {info['userAllocatedNatIps']}, Num VMs: {info['numVmEndpointsWithNatMappings']}")


def get_firewall_rules(resource_object, project_id):

    firewall_rules = []

    page_token = None
    while True:
        _ = resource_object.firewalls().list(project=project_id).execute()
        firewall_rules.extend(_.get('items', []))
        page_token = _.get('nextPageToken')
        del(_)
        if not page_token:
            break

    return firewall_rules


def get_addresses(resource_object, project_id, options={}):

    addresses = []

    try:
        _ = resource_object.addresses().aggregatedList(project=project_id).execute()
        items = _.get('items', {})
    except Exception as e:
        return []

    for item in parse_aggregated_results(items, 'addresses'):
        info = {
            'address': item.get('address'),
            'name': item.get('name'),
            'project_id': project_id,
            'type': item.get('addressType', "unknown"),
            'region': item.get('region'),
            'purpose': item.get('purpose'),
            'subnet_name': None,
        }
        if 'subnetwork' in item:
            info['subnet_name'] = item.get('subnetwork').split('/')[-1]
        addresses.append(info)

    #return addresses
    yield addresses

def get_instances(resource_object, project_id):

    instances = []

    try:
        _ = resource_object.instances().aggregatedList(project=project_id).execute()
        items = _.get('items', {})
    except Exception as e:
        return []

    for item in parse_aggregated_results(items, 'instances'):
        info = {
            'name': item.get('name'),
            'project_id': project_id,
            'zone': item.get('zone').split('/')[-1],
            'machine_type': item.get('machineType').split('/')[-1],
            'ip_forwarding': item.get('canIpForward', False),
            'status': item.get('status', "UNKNOWN"),
        }
        for nic in item.get('networkInterfaces', []):
            info['address'] = item.get('networkIP')
            if 'network' in nic:
                info['network_name'] = nic.get('network').split('/')[-1]
            if 'subnetwork' in nic:
                info['subnet_name'] = nic.get('subnetwork').split('/')[-1]
        instances.append(info)

    return instances

    """
                 Look for external IP addresses (access configs)
                    for ac in nic.get('accessConfigs', []):
                        item = {
                            'address': ac.get('natIP'),
                            'name': nic.get('name'),
                            'project_id': project_id,
                            'type': ac.get('type'),
                            'region': REGION,
                        }
                        instances.append(instance)
    """


def parse_forwarding_rules(items: list = []) -> list:

    results = []
    for item in items:
        #print(item)
        if 'ports' in item:
            ports = item.get('ports')
        elif 'portRange' in item:
            ports = item.get('portRange').split("-")
        else:
            ports = "all"
            #ports = list(set(ports.split("-")))
        info = {
            #'project_id': project_id,
            'name': item.get('name'),
            'ip_address': item.get('IPAddress'),
            'protocol': item.get('IPProtocol'),
            'ports': str(ports),
            'region': "global",
            'type': item.get('loadBalancingScheme', 'UNKNOWN'),
            'global_access': item.get('allowGlobalAccess', False),
        }
        if 'target' in item:
            info['target'] = item.get('target').split('/')[-1]
        if 'backendService' in item:
            info['backend_service'] = item.get('backendService').split('/')[-1]
        if 'network' in item:
            info['network_name'] = item.get('network').split('/')[-1]
            info['network_project'] = item.get('network') #.split('')[-4]
            info['subnet_name'] = item.get('subnetwork') #.split('/')[-1]
        results.append(info)

    return results


def get_forwarding_rules(resource_object, project_id: str) -> list:

    forwarding_rules = []

    # Global forwarding rules
    try:
        _ = resource_object.globalForwardingRules().list(project=project_id).execute()
        items = _.get('items', [])
    except Exception as e:
        items = []

    for item in items:
        forwarding_rules.append(item)

    # Regional Forwarding Rules
    try:
        _ = resource_object.forwardingRules().aggregatedList(project=project_id).execute()
        items = _.get('items', {})
    except Exception as e:
        items = {}
    for item in parse_aggregated_results(items, 'forwardingRules'):
        info = item
        forwarding_rules.append(info)

    return forwarding_rules


def get_url_maps(resource_object, project_id: str) -> list:

    url_maps = []

    try:
        _ = resource_object.urlMaps().aggregatedList(project=project_id).execute()
        items = _.get('items', {})
    except Exception as e:
        items = {}
    for item in parse_aggregated_results(items, 'urlMaps'):
        info = item
        url_maps.append(info)

    return url_maps

"""
_ = resource_object.urlMaps().list(project=PROJECT_ID).execute()
url_maps = _.get('items', [])
for url_map in url_maps:
    if url_map['name'].startswith("test"):
        pprint(url_map)
    redirect = False
    if 'defaultUrlRedirect' in url_map:
        redirect = True
    default_service = url_map.get('defaultService')
    if default_service:
        default_service = default_service.split('/')[-1]
    print(f" Name: {url_map['name']}, Redirect: {redirect}, Default service: {default_service}")
"""

