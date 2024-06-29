from aiohttp import ClientSession
from asyncio import gather, run

URL = "https://css.test.ca.opentext.com/health/ready"
USER_AGENT = "Apache-HttpClient/4.5.13 (Java/12.0.2)"


async def make_request(url: str):

    try:
        headers = {'User-Agent': USER_AGENT}
        params = {}
        async with ClientSession(raise_for_status=True) as session:
            async with session.get(url, headers=headers, params=params) as response:
                if int(response.status) == 200:
                    return response
                else:
                    raise response
    except Exception as e:
        await session.close()


async def main():

    url = "https://www.j5.org"
    tasks = [make_request(url) for i in range(0, 256)]
    _ = await gather(*tasks)
    return([response.status for response in _])

if __name__ == '__main__':

    _ = run(main())
    print(_)
