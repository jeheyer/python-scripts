import asyncio
from gcloud.aio.auth import Token
from gcloud.aio.storage import Storage
from time import time
from datetime import datetime

async def list_objects(bucket_name, prefix = "") -> list:

    token = Token(scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"])
    async with Storage(token=token) as storage:
        # tasks = (client.list_objects(bucket_name, timeout=3) for bucket_name in [bucket_name])
        # _ = await gather(*tasks)
        _ = await storage.list_objects(bucket_name, timeout=3)
    await token.close()

    blobs = []
    for b in _.get('items', []):
        print(b['updated'])
        mdy = b['updated'][:10]
        hms = b['updated'][11:19]
        #print(mdy, hms)
        timestamp = datetime.timestamp(datetime.strptime(mdy + hms, "%Y-%m-%d%H:%M:%S"))
        #print(timestamp)
        blobs.append(b['name'])
    return blobs

start_time: time = time()
blobs = asyncio.run(list_objects("otc-core-network-prod", "squid/logs/"))
print("seconds_to_execute:", round((time() - start_time), 3))
#print(blobs)
