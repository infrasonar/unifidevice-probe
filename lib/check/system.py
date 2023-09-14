import aiohttp
from libprobe.asset import Asset
from lib.unificonn import get_session


async def check_system(
    asset: Asset,
    asset_config: dict,
    check_config: dict
) -> dict:
    site_name = check_config.get('site', 'default')
    ssl = check_config.get('ssl', True)
    url = f'/api/s/{site_name}/stat/sysinfo'
    ...
