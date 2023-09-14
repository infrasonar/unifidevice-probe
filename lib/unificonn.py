import aiohttp
import logging
import os
from libprobe.asset import Asset
from libprobe.exceptions import CheckException
from lib.asset_cache import AssetCache


async def login(asset: Asset, asset_config: dict, check_config: dict) -> dict:
    logging.debug(f'login on asset {asset}')

    address = check_config.get('address')
    if not address:
        address = asset.name
    port = check_config.get('port', 443)
    ssl = check_config.get('ssl', True)
    username = asset_config.get('username')
    password = asset_config.get('password')

    auth_data = {
        'username': username,
        'password': password,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'https://{address}:{port}/api/login',
            json=auth_data,
            ssl=ssl,
        ) as resp:
            if resp.status // 100 == 2:
                return {
                    'base_url': f'https://{address}:{port}',
                    'cookies': resp.cookies,
                }
            else:
                raise CheckException('login failed')


async def get_session(asset: Asset, asset_config: dict,
                      check_config: dict) -> dict:
    session, _ = AssetCache.get_value(asset)
    if session:
        return session

    try:
        session = await login(asset, asset_config, check_config)
    except ConnectionError:
        raise CheckException('unable to connect')
    except Exception:
        raise
    else:
        AssetCache.set_value(asset, session)
    return session
