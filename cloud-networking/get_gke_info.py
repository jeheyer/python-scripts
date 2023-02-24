#!/usr/bin/env python3

from gcp_api import *
from os import environ
from collections import Counter
from pprint import pprint


def get_gke_clusters(resource_object, project_id: str) -> list:

    try:
        parent = f"projects/{project_id}/locations/-"
        _ = resource_object.projects().locations().clusters().list(parent=parent).execute()
        return _.get('clusters', [])
    except:
        return []


def main():

    clusters = []

    network_name = environ.get('NETWORK_NAME', "default")

    try:
        resource_object = connect_to_api(api_name="container",version="v1")
        for PROJECT_ID in get_project_ids():
            for cluster in get_gke_clusters(resource_object, PROJECT_ID):
                if not network_name:
                    clusters.append(cluster)
                else:
                    if cluster.get('network') == network_name:
                        clusters.append(cluster)

    except Exception as e:
        quit(e)

    cluster_versions = [ c.get('currentNodeVersion', "unknown") for c in clusters ]
    version_count = Counter(cluster_versions)
    pprint(version_count)
    cluster_zones = [ c.get('zone', "unknown") for c in clusters ]
    print(Counter(cluster_zones))


if __name__ == "__main__":

    main()