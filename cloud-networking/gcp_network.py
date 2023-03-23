import ipaddress
from datetime import datetime
from gcp_api import *


def get_networks(resource_object, project_id: str) -> list:

    networks = []
    vpc_peerings = []

    try:
        _ = resource_object.networks().list(project=project_id).execute()
        items = _.get('items', [])
    except Exception as e:
        items = []

    #print("Found", len(items), "networks in project ID", project_id)

    for item in items:
        info = {
            'project_id': project_id,
            'name': item.get('name'),
            'description': item.get('description'),
            'routing_mode': item.get('routingConfig', "UNKNOWN"),
        }
        if 'routingConfig' in item:
            routing_config = item.get('routingConfig')
            info['routing_mode'] = routing_config.get('routingMode', "UNKNOWN")
        for peering in item.get('peerings', []):
            #print(peering.get('name'))
            peer_info = {
                'project_id': project_id,
                'network_name': item['name'],
                'name': peering.get('name'),
                #'peer_project_id': peering['network'].split('/')[-4],
                #'peer_network_name': peering['network'].split('/')[-1],
                'peer_mtu': peering.get('peerMtu', 0),
                'stack_type': peering.get('stackType', "UNKNOWN"),
                'state': peering.get('state', "UNKNOWN"),
            }
            #print(peer_info)
            vpc_peerings.append(peer_info)
        networks.append(info)

    return networks, vpc_peerings


def get_ssl_certs(resource_object, project_id: str) -> list:

    ssl_certs = []

    # Global
    try:
        _ = resource_object.sslCertificates().list(project=project_id).execute()
        items = _.get('items', [])
    except Exception as e:
        items = []

    for item in items:

        info = {
            'project_id': project_id,
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

    try:
        _ = resource_object.projects().listXpnHosts(project=project_id, body={}).execute()
        return [p['name'] for p in _.get('items', [])]
    except Exception as e:
        raise e


def get_routes(resource_object, project_id: str) -> {}:

    """
    Get list of all routes, project level
    """

    routes = []
    routes_per_network = {}

    page_token = None
    while True:
        try:
            _ = resource_object.routes().list(project=project_id, pageToken=page_token).execute()
            items = _.get('items', [])
            page_token = _.get('nextPageToken')
        except Exception as e:
            break

        for item in items:
            network_name = item.get('network').split('/')[-1]
            info = {
                'name': item.get('name'),
                'destRange': item.get('destRange'),
                'project_id': project_id,
                'network_name': network_name,
                'priority': item.get('priority'),
            }
            if 'creationTimestamp' in item:
                created_ymd = item['creationTimestamp'][:10]  # Read Year, Monday, Day from expireTime field
                info['created'] = datetime.timestamp(datetime.strptime(created_ymd, "%Y-%m-%d"))
            routes.append(info)

            #if not network_name in routes_per_network:
            #    routes_per_network[network_name] = []
            #routes_per_network[network_name].append(info)

        # Check for a next page token in the response; if one isn't present, we're done
        if not page_token:
            break

    return routes


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
            'project_id': project_id,
            'num_interfaces': len(item.get('interfaces', [])),
        }
        cloud_routers.append(info)

    return cloud_routers


def get_cloud_router_routes(resource_object, project_id: str, cloud_router_name: str, region_name: str) -> list:

    """
    Get full list of routes from a given cloud router
    """

    routes = []

    _ = resource_object.routers().getRouterStatus(project=project_id, region=region_name, router=cloud_router_name).execute()
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
        del _
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

    fields = {
        'address': "address",
        'name': "name"
    }

    for item in parse_aggregated_results(items, 'addresses'):
        info = {
            'address': item.get('address'),
            'name': item.get('name'),
            'description': item.get('description'),
            'project_id': project_id,
            'type': item.get('addressType', "unknown"),
            'region': item.get('region'),
            'purpose': item.get('purpose'),
            'tier': item.get('networkTier'),
            'network_name': None,
            'subnet_name': None,
            'prefix': None,
        }
        if 'network' in item:
            info['network_name'] = item.get('network').split('/')[-1]
        if 'subnetwork' in item:
            info['subnet_name'] = item.get('subnetwork').split('/')[-1]
        addresses.append(info)

    # Global Addresses
    try:
        _ = resource_object.globalAddresses().list(project=project_id).execute()
        items = _.get('items', [])
    except Exception as e:
        items = []

    for item in items:
        #print(item)
        info = {
            'address': item.get('address'),
            'name': item.get('name'),
            'description': item.get('description'),
            'project_id': project_id,
            'type': item.get('addressType', "unknown"),
            'region': "global",
            'purpose': item.get('purpose'),
            'tier': item.get('networkTier'),
            'network_name': None,
            'subnet_name': None,
            'prefix': None,
        }
        if 'network' in item:
            info['network_name'] = item.get('network').split('/')[-1]
        if 'subnetwork' in item:
            info['subnet_name'] = item.get('subnetwork').split('/')[-1]
        if 'prefixLength' in item:
            info['address'] = info['address'] + "/" + str(item.get('prefixLength'))
        #info['region'] == "global"

        addresses.append(info)

    return addresses


def get_vpn_tunnels(resource_object, project_id) -> list:

    vpn_tunnels = []

    try:
        _ = resource_object.vpnTunnels().aggregatedList(project=project_id).execute()
        items = _.get('items', {})
    except Exception as e:
        return []

    for item in parse_aggregated_results(items, 'vpnTunnels'):
        info = {
            'project_id': project_id,
            'name': item.get('name'),
            'region': item.get('region'),
            'vpn_gateway': item['vpnGateway'].split('/')[-1] if 'vpnGateway' in item else None,
            'interface': item.get('vpnGatewayInterface'),
            'peer_gateway': item['peerExternalGateway'].split('/')[-1] if 'peerExternalGateway' in item else None,
            'peer_ip': item.get('peerIp'),
            'ike_version': item.get('ikeVersion', 0),
            'status': item.get('status'),
        }
        vpn_tunnels.append(info)

    return vpn_tunnels


def get_interconnects(resource_object, project_id) -> list:

    interconnects = []

    try:
        _ = resource_object.interconnectAttachments().aggregatedList(project=project_id).execute()
        items = _.get('items', {})
    except Exception as e:
        return []

    for item in parse_aggregated_results(items, 'interconnectAttachments'):
        info = {
            'project_id': project_id,
            'name': item.get('name'),
            'type': item.get('type', "UNKNOWN"),
            'admin_enabled': item.get('adminEnabled', "UNKNOWN"),
            'state': item.get('state', "UNKNOWN"),
            'bandwidth': item.get('bandwidth', "UNKNOWN"),
            'region': item.get('region'),
            'pairing_key': item.get('pairingKey', "NONE"),
            'cloud_router_ip': item.get('cloudRouterIpAddress'),
            'customer_router_ip': item.get('customerRouterIpAddress'),
            'encryption': item.get('encryption', "UNKNOWN"),
            'mtu': item.get('mtu', 0),
            'vlan_tag': item.get('vlanTag8021q', 1),
        }
        if 'router' in item:
            info['cloud_router'] = item.get('router').split('/')[-1]
        if 'partnerMetadata' in item:
            metadata = item['partnerMetadata']
            info['partner_name'] = metadata.get('partnerName', "UNKNOWN")
            info['interconnect_name'] = metadata.get('interconnectName', "UNKNOWN")
            info['partner_portal'] = metadata.get('portalUrl')
        if 'creationTimestamp' in item:
            created_ymd = item['creationTimestamp'][:10]
            info['created'] = datetime.timestamp(datetime.strptime(created_ymd, "%Y-%m-%d"))
        interconnects.append(info)

    return interconnects


def get_instances(resource_object, project_id) -> list:

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
            #print(item)
            info['address'] = nic.get('networkIP')
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
        #print(item)
        info = {
            'project_id': project_id,
            'name': item.get('name'),
            'ip_address': item.get('IPAddress'),
            'lb_scheme': item.get('loadBalancingScheme'),
            'region': "global",
            'network_name': None,
            'subnet_name': None,
        }
        if 'ports' in item:
            ports = str(item.get('ports', "none"))
        elif 'portRange' in item:
            ports = str(item.get('portRange').split("-"))
        else:
            ports = "all"
        info['ports'] = ports
        if 'network' in item:
            info['network_name'] = item.get('network').split('/')[-1]
        if 'subnetwork' in item:
            info['subnet_name'] = item.get('subnetwork').split('/')[-1]
        forwarding_rules.append(info)

    # Regional Forwarding Rules
    try:
        _ = resource_object.forwardingRules().aggregatedList(project=project_id).execute()
        items = _.get('items', {})
    except Exception as e:
        items = {}
    for item in parse_aggregated_results(items, 'forwardingRules'):
        #print(item)
        info = {
            'project_id': project_id,
            'name': item.get('name'),
            'ip_address': item.get('IPAddress'),
            'lb_scheme': item.get('loadBalancingScheme'),
            'region': item.get('region', "global"),
            'network_name': None,
            'subnet_name': None,
        }
        if 'ports' in item:
            ports = str(item.get('ports', "none"))
        elif 'portRange' in item:
            ports = str(item.get('portRange').split("-"))
        else:
            ports = "all"
        info['ports'] = ports
        if 'network' in item:
            info['network_name'] = item.get('network').split('/')[-1]
        if 'subnetwork' in item:
            info['subnet_name'] = item.get('subnetwork').split('/')[-1]
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

