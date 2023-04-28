import asyncio
from gcp_api import *

token = get_bearer_token()
project_id = "otc-vpc-shared"
call = "global/networks"

asyncio.run(make_api_call(project_id, call, token)

