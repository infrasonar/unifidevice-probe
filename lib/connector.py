from typing import Optional
import aiohttp
import asyncio


def get_connector(
            loop: Optional[asyncio.AbstractEventLoop] = None
        ) -> aiohttp.TCPConnector:
    if loop is None:
        loop = asyncio.get_running_loop()

    return aiohttp.TCPConnector(
        limit=100,  # 100 is default
        use_dns_cache=False,
        enable_cleanup_closed=True,
        force_close=True,
        loop=loop,
    )
