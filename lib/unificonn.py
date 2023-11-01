import aiohttp
import logging
import os
from libprobe.asset import Asset
from libprobe.exceptions import CheckException, IgnoreResultException
from lib.connection_cache import ConnectionCache


async def login(controller: str, port: int, ssl: bool,
                username: str, password: str) -> dict:
    logging.debug(f'login on controller {controller}')

    auth_data = {
        'username': username,
        'password': password,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'https://{controller}:{port}/api/auth/login',
                json=auth_data,
                ssl=ssl,
            ) as resp:
                resp.raise_for_status()
                return {
                    'base_url': f'https://{controller}:{port}',
                    'cookies': resp.cookies,
                }
    except Exception as e:
        msg = str(e) or type(e).__name__
        raise CheckException(f'login failed: {msg}')


async def get_session(asset: Asset, asset_config: dict,
                      check_config: dict) -> dict:

    controller = check_config.get('controller')
    if controller is None:
        msg = 'missing controller in collector configuration'
        raise CheckException(msg)

    port = check_config.get('port', 443)
    ssl = check_config.get('ssl', False)
    username = asset_config.get('username')
    password = asset_config.get('password')
    if None in (username, password):
        logging.error(f'missing credentials for {asset}')
        raise IgnoreResultException

    # we use everything what identifies a connection for an asset as key
    # of the cached 'connection'
    connection_args = (controller, port, ssl, username, password)
    session = ConnectionCache.get_value(connection_args)
    if session:
        return session

    try:
        session = await login(*connection_args)
    except ConnectionError:
        raise CheckException('unable to connect')
    except Exception:
        raise
    else:
        # when connection is older than 3600 we request new 'connection'
        max_age = 3600
        ConnectionCache.set_value(connection_args, session, max_age)
    return session
