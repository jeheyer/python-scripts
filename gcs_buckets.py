#!/usr/bin/env python3 

from oauth2client.client import GoogleCredentials
from googleapiclient import discovery
from google.cloud import storage
from gcloud.aio.auth import Token
from gcloud.aio.storage import Storage
from asyncio import run, gather

SCOPES = ["https://www.googleapis.com/auth/cloud-platform.read-only"]


async def get_projects() -> list:

    try:
        _ = GoogleCredentials.get_application_default()
        _ = discovery.build('cloudresourcemanager', 'v1', credentials=_)
        _ = _.projects().list().execute()
    except Exception as e:
        quit(e)
    return ["otl-ems-netops", "otl-network-poc", "otl-core-network-pre-comm", "otl-pre-comm", "otl-vpc-shared"]
    return [project['projectId'] for project in _.get('projects', [])]


def get_buckets(project_id: str) -> list:

    try:
        _ = storage.Client(project=project_id)
        _ = _.list_buckets()
        return [bucket.name for bucket in _]
    except Exception as e:
        return []


async def get_objects(project_id: str, bucket_name: str) -> list:

    objects = []
    token = Token(service_file=None, scopes=SCOPES)
    objects = []
    params = {'prefix': '/'}

    try:
        async with Storage(token=token) as storage:
            while True:
                _ = await storage.list_objects(bucket_name, params=params, timeout=10)
                for o in _.get('items', []):
                    if size := int(o.get('size', 0)) > 0:  # Ignore zero byte files
                        updated_mdy = o['updated'][:10]
                        updated_hms = o['updated'][11:19]
                        #updated = datetime.timestamp(datetime.strptime(updated_mdy + updated_hms, "%Y-%m-%d%H:%M:%S"))
                        objects.append({'name': o['name']})
                if page_token := _.get('nextPageToken'):
                    params['pageToken'] = page_token
                else:
                    break
        await token.close()

    except Exception as e:
        raise e

    return objects


    return []


async def main():

    project_ids = await get_projects()
    #buckets = [get_buckets(project_id) for project_id in project_ids]
    #print(buckets)
    tasks = [{project_id: get_buckets(project_id)} for project_id in project_ids]
    results = await gather(*tasks)
    #print(dict(zip(project_ids, results)))

if __name__ == "__main__":
    run(main())
