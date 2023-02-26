from asyncio import gather
from os import path
from gcloud.aio.auth import Token
from gcloud.aio.storage import Storage
from boto3 import Session
from io import BytesIO
from datetime import datetime


def authenticate_to_gcs(service_file: str = None):

    scopes = ["https://www.googleapis.com/auth/cloud-platform.read-only"]

    try:
        if service_file:
            pwd = path.realpath(path.dirname(__file__))
            service_file = path.join(pwd, service_file)
            token = Token(service_file=service_file, scopes=scopes)
        else:
            token = Token(scopes=scopes)
    except Exception as e:
        raise e

    return token


async def get_objects_list(bucket_name: str, prefix: str = "", bucket_type: str = 'gcs', credentials_file: str = None) -> list:

    objects = []

    try:
        if 'gcs' in bucket_type or 'google' in bucket_type:

            token = authenticate_to_gcs(credentials_file)
            params = {'prefix': prefix}
            async with Storage(token=token) as storage:
                _ = await storage.list_objects(bucket_name, params=params, timeout=3)
            await token.close()

            for o in _.get('items', []):
                if int(o.get('size', 0)) > 0:
                    updated_mdy = o['updated'][:10]
                    updated_hms = o['updated'][11:19]
                    updated = datetime.timestamp(datetime.strptime(updated_mdy + updated_hms, "%Y-%m-%d%H:%M:%S"))
                    objects.append({'name': o['name'], 'updated': updated})


    except Exception as e:
        raise e

    return objects


async def read_files_from_bucket(bucket_name: str, file_names: list, bucket_type: str = 'gcs', credentials_file: str = None) -> str:

    try:

        if 'gcs' in bucket_type or 'google' in bucket_type:

            token = authenticate_to_gcs(credentials_file)

            # Fetch the files
            async with Storage(token=token) as storage:
                tasks = (storage.download(bucket_name, file_name) for file_name in file_names)
                blobs = await gather(*tasks)
            await token.close()

            return blobs

        if 's3' in bucket_type or 'aws' in bucket_type:
            s3_client = Session().client("s3")
            fh = BytesIO()
            s3_client.download_fileobj(bucket_name, file_name, fh)
            fh.seek(0)
            return fh.getvalue()

        return ""

    except Exception as e:
        raise e
