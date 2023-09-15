import aiohttp
import logging
import os
from libprobe.asset import Asset
from libprobe.exceptions import CheckException, IgnoreResultException
from lib.asset_cache import AssetCache


async def login(asset: Asset, asset_config: dict, check_config: dict) -> dict:
    logging.debug(f'login on asset {asset}')

    controller = check_config.get('controller')
    if controller is None:
        msg = 'missing controller in collector configuration'
        raise CheckException(msg)

    port = check_config.get('port', 443)
    ssl = check_config.get('ssl', False)
    username = asset_config.get('username')
    password = asset_config.get('password')
    if None in (username, password):
        logging.error(f'missing credentails for {asset}')
        raise IgnoreResultException

    auth_data = {
        'username': username,
        'password': password,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'https://{controller}:{port}/api/login',
            json=auth_data,
            ssl=ssl,
        ) as resp:
            if resp.status // 100 == 2:
                return {
                    'base_url': f'https://{controller}:{port}',
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
