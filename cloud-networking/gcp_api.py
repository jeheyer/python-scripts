from googleapiclient import discovery
from google.oauth2 import service_account


def connect_to_api(api_name='compute', version='v1', credentials_file=None):

    try:
        if credentials_file:
            credentials = service_account.Credentials.from_service_account_file(credentials_file)
        else:
            credentials = None
        resource_object = discovery.build(api_name, version, credentials=credentials)
    except Exception as e:
        raise(e)

    return resource_object

def get_projects():

    """
    Get a list of all GCP Projects
    """

    try:
        _ = connect_to_api(api_name='cloudresourcemanager', version='v1')
        _ = _.projects().list().execute()
        return _.get('projects', [])
    except Exception as e:
        quit(e)


def get_project_ids() -> list:

    """
    Get list of all GCP project IDs we have access to
    """

    return [ project.get('projectId') for project in get_projects() ]


def get_regions(resource_object, project_id: str) -> list:

    """
    Get list of all GCP regions
    Note - GetZones() is much faster and provides region name as the key
    """

    _ = resource_object.regions().list(project=project_id).execute()
    return [ region.get('name') for region in _.get('items', []) ]


def get_zones(resource_object, project_id: str) -> list:

    """
    Get Zones with Region name as key
    """

    _ = resource_object.zones().list(project=project_id).execute()
    zones = _.get('items', [])
    for zone in zones:
        if zone.get('status') != "UP":
            continue  # Ignore zones that aren't available
        region_name = zone['region'].split('/')[-1]
        if not region_name in zones:
            zones[region_name] = list()
        zones[region_name].append(zone.get('name'))

    return zones


def parse_aggregated_results(results: dict, key: str) -> list:

    items = []
    for k, v in results.items():
        if k == 'global':
            region = 'global'
        else:
            region = k.split('/')[1]
        for item in results[k].get(key, []):
            item['region'] = region
            items.append(item)
    return items
