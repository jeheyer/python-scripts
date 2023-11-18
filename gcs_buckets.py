#!/usr/bin/env python3 

from oauth2client.client import GoogleCredentials
from asyncio import run, gather, create_task
from aiohttp import ClientSession
import yaml


async def make_async_call(url: str, access_token: str, key: str = 'items') -> list:

    results = []

    try:
        headers = {'Authorization': f"Bearer {access_token}"}
        async with ClientSession(raise_for_status=True) as session:
            page_token = None
            while True:
                params = {'pageToken': page_token} if page_token else {}
                async with session.get(url=url, headers=headers, params=params) as response:
                    if int(response.status) == 200:
                        data = await response.json()
                        results.extend(data.get(key, []))
                        if page_token := data.get('nextPageToken'):
                            params.update({'pageToken': page_token})
                        else:
                            break
        return results
    except Exception as e:
        return []


async def get_projects(access_token: str) -> list:

    try:
        url = "https://cloudresourcemanager.googleapis.com/v1/projects"
        projects = await make_async_call(url, access_token, key='projects')
        _ = {}
        for project in projects:
            _.update({int(project['projectNumber']): project['projectId']})
        return _
    except Exception as e:
        quit(e)


async def get_buckets(project_id: str, access_token: str) -> list:

    try:
        url = f"https://storage.googleapis.com/storage/v1/b?project={project_id}"
        return await make_async_call(url, access_token)
    except Exception as e:
        print(e)
        return []


async def get_objects(bucket_name: str, access_token: str):

    total_size = 0
    params = {'prefix': ''}
    try:
        url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o?prefix="
        _ = await make_async_call(url, access_token)
        num_objects = len(_)
        for o in _:
            if size := int(o.get('size', 0)):
                total_size += size
        return num_objects, total_size
    except Exception as e:
        print(e)
        return []


async def main():

    try:
        creds = GoogleCredentials.get_application_default()
        access_token = creds.get_access_token().access_token
        projects = await get_projects(access_token)

        tasks = []
        for project_id in ["otc-core-network-prod-4aea"]: #projects.values():
            tasks.append(create_task(get_buckets(project_id, access_token)))
        buckets = []
        for _ in await gather(*tasks):
            buckets.extend(_)
        for bucket in buckets:
            _ = {
                'name': bucket.get('name'),
                'location': bucket.get('location', 'UNKNOWN').lower(),
                'class': bucket.get('storageClass', 'UNKNOWN'),
                'project_id': projects.get(int(bucket['projectNumber']), "error"),
            }
            _['num_objects'], _['total_size'] = await get_objects(_['name'], access_token)
            print(_)
    except Exception as e:
        quit(e)

if __name__ == "__main__":
    run(main())
