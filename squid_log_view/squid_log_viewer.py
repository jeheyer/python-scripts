from asyncio import run
from collections import deque, Counter
from time import time
from math import floor
from yaml import load, FullLoader
from cloud_storage import *

LOG_FIELD_NAMES: tuple = ('timestamp', 'elapsed', 'client_ip', 'code', 'bytes', 'method', 'url', 'rfc931', 'peer_status', 'type')
FILTER_FIELD_NAMES: tuple = ('client_ip', 'code', 'url')
DEFAULT_INTERVAL: int = 1800
DEFAULT_FILTER: dict = {}


def process_log(blob, time_range: tuple, filter: dict = {}) -> list:

    try:

        lines = blob.decode('utf-8').splitlines()

        if filter:
            filter_indexes: dict = {}
            for i, field_name in enumerate(LOG_FIELD_NAMES):
                if field_name in filter:
                    filter_indexes[i] = field_name

        # Work backwards on file, since newer entries are at the end
        for _ in range(len(lines)-1, 0, -1):
            line: str = lines[_]
            timestamp: int = int(line[:10])
            if timestamp < time_range[0]:
                break  # read too far
            if timestamp > time_range[1]:
                continue  # haven't read enough
            # Found a line in the time range
            entry: list = line.split()
            if entry[3] == "NONE/000":
                continue
            if entry[6].startswith("http:"):
                # Remove full URL from HTTP requests
                host = entry[6][7:].split('/')[0]
                if ":" in host:
                    entry[6] = host
                else:
                    entry[6] = host + ":80"
            if filter:
                match = False
                for i, field_name in filter_indexes.items():
                    if filter[field_name] in entry[i]:
                        match = True
                    else:
                        match = False
                        break
                if match:
                    yield entry
            else:
                yield entry

    except Exception as e:
        raise e


def get_squid_data(env_vars: dict = {}) -> dict:

    pwd = path.realpath(path.dirname(__file__))
    locations_file = path.join(pwd, 'locations.yaml')
    with open(locations_file) as file:
        locations = load(file, Loader=FullLoader)

    # Process parameters
    if 'action' in env_vars:
        action: str = env_vars.get('action', None)
        if action == "get_locations":
            return list(locations.keys())
        if action == "get_clusters":
            location: str = env_vars.get('location')
            return list(locations[location]['clusters'].keys())

    # Parse parameters to determine time range
    interval = int(env_vars['interval']) if 'interval' in env_vars else DEFAULT_INTERVAL
    end_time = int(env_vars['end_time']) if 'end_time' in env_vars else floor(time())
    start_time = int(env_vars['start_time']) if 'start_time' in env_vars else end_time - interval
    time_range = (start_time, end_time)

    # Parse parameters to determine filter
    filter: dict = DEFAULT_FILTER
    for f in FILTER_FIELD_NAMES:
        if f in env_vars and env_vars[f] != "":
            filter[f] = env_vars[f]

    # Populate hosts
    hosts: dict = {}
    if 'location' in env_vars:
        location = env_vars.get('location')
        hosts[location] = {}
        bucket_name = locations[location]['bucket_name']
        bucket_type = locations[location]['bucket_type']
        file_path = locations[location]['file_path']
        credentials_file = locations[location]['credentials_file']
        if 'cluster' in env_vars:
            cluster = env_vars.get('cluster')
            hosts[location][cluster] = locations[location]['clusters'][cluster]
        else:
            for cluster in locations[location]['clusters']:
                hosts[location][cluster] = locations[location]['clusters'][cluster]

    """
    hits_by_host: dict = {}
    hits_by_cluster: dict = {}
    file_names = {}
    for location in hosts.keys():
        for cluster in hosts[location].keys():
            cluster_id = location + ":" + cluster
            hits_by_cluster[cluster_id] = 0
            for host in hosts[location][cluster]:
                hits_by_host[host] = 0
                file_names[host] = file_path + host + ".log"

    file_names.clear()
    """
    # Get a list of all files in the bucket
    objects = run(get_objects_list(bucket_name, prefix=file_path, bucket_type=bucket_type, credentials_file=credentials_file))

    # Populate list of files to read from bucket
    file_names: dict = {}
    hits_by_host: dict = {}
    for o in objects:
        if o['updated'] < start_time:
            continue
        host = o['name'].split('/')[-1].replace('.log', '')
        if 'us-east4' in host:
            file_names[host] = o['name']
            hits_by_host[host] = 0

    #file_names.clear()
    #file_names[host] = o['name']
    #return file_names


    # Read the log files from the bucket
    entries: deque = deque()
    blobs = run(read_files_from_bucket(bucket_name, file_names.values(), bucket_type=bucket_type, credentials_file=credentials_file))
    for i, host in enumerate(file_names.keys()):
        matches = list(process_log(blobs[i], time_range, filter))
        if len(matches) > 0:
            entries.extend(matches)
            hits_by_host[host] = len(matches)
            #hits_by_cluster[cluster_id] += hits_by_host[host]
    del blobs

    # Sort by timestamp reversed, so that newest entries are first
    newest_first: list = sorted(entries, key=lambda x: x[0][:10], reverse=True)
    entries.clear()

    # Convert to list of dictionaries
    requests_by_client = {}; status_code_counts = {}; bytes_by_client_ip = {}; requests_by_method = {}; requests_by_domain = {}; peer_status_counts = {}
    for _ in newest_first:
        requests_by_client[_[2]] = requests_by_client[_[2]]+1 if _[2] in requests_by_client else 1
        bytes_by_client_ip[_[2]] = bytes_by_client_ip[_[2]] + int(_[4]) if _[2] in bytes_by_client_ip else int(_[4])
        status_code_counts[_[3]] = status_code_counts[_[3]]+1 if _[3] in status_code_counts else 1
        requests_by_method[_[5]] = requests_by_method[_[5]]+1 if _[5] in requests_by_method else 1
        if _[6].startswith("http:"):
            domain: str = _[6][7:].split("/")[0]
            if not ":" in domain:
                domain = domain + ":80"
        else:
            domain = _[6]
        requests_by_domain[domain] = requests_by_domain[domain]+1 if domain in requests_by_domain else 1
        peer_status = _[8].split("/")[0]
        peer_status_counts[peer_status] = peer_status_counts[peer_status]+1 if peer_status in peer_status_counts else 1
        entries.append(dict(zip(LOG_FIELD_NAMES, _)))

    return {
        'entries': list(entries),
        #'hits_by_cluster': hits_by_cluster,
        'hits_by_host': hits_by_host,
        'requests_by_client_ip': {k: v for k, v in sorted(requests_by_client.items(), key=lambda item: item[1], reverse=True)},
        'requests_by_method': {k: v for k, v in sorted(requests_by_method.items(), key=lambda item: item[1], reverse=True)},
        'requests_by_domain': {k: v for k, v in sorted(requests_by_domain.items(), key=lambda item: item[1], reverse=True)},
        'hits_by_status_code': status_code_counts,
        'bytes_by_client_ip': bytes_by_client_ip,
        'peer_status_counts': peer_status_counts
    }
