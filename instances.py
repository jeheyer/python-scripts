#!/usr/bin/env python3 

from asyncio import run, gather, create_task
from collections import Counter
from google.auth import default
from google.auth.transport.requests import Request
from gcp_functions import make_async_call


async def get_projects(access_token: str) -> list:

    url = "https://cloudresourcemanager.googleapis.com/v1/projects"
    try:
        projects = await make_async_call(url, access_token, key='projects')
        return [project['projectId'] for project in projects]
    except Exception as e:
        raise e


async def get_nics(project_id: str, access_token: str) -> list:

    nics = []

    url = f"compute/v1/projects/{project_id}/aggregated/instances"
    try:
        instances = await make_async_call(url, access_token)
    except:
        return []

    for instance in instances:
        for nic in instance.get('networkInterfaces', []):
            if network := nic.get('network'):
                network_name = network.split('/')[-1]
                network_project_id = network.split('/')[-4]
                zone = instance.get('zone', 'null/unknown-0')
                nics.append({
                    'name': instance['name'],
                    'network_id': f"{network_project_id}/{network_name}",
                    'region': zone.split('/')[-1][:-2],
                })
    return nics


async def main():

    try:
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        credentials, project_id = default(scopes=scopes, quota_project_id=None)
        credentials.refresh(Request())
        access_token = credentials.token
        project_ids = await get_projects(access_token)
    except Exception as e:
        quit(e)
    #print(project_ids)

    print(f"Counting instances across {len(project_ids)} projects...")

    tasks = [create_task(get_nics(p, access_token)) for p in project_ids]
    nics = []
    for _ in await gather(*tasks):
        nics.extend(_)
    #print(nics)

    counter = {}
    print(Counter([nic['network_id'] for nic in nics]))

    network_ids = set([nic['network_id'] for nic in nics])
    for network_id in network_ids:
        counter[network_id] = Counter([nic['region'] for nic in nics if network_id == nic['network_id']])
    [print(f"{k}:{v}") for k, v in counter.items()]

if __name__ == "__main__":
    run(main())
