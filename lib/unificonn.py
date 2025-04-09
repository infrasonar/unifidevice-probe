import aiohttp
import logging
import os
from typing import Tuple
from libprobe.asset import Asset
from libprobe.exceptions import CheckException, IgnoreResultException
from lib.connection_cache import ConnectionCache
from .connector import get_connector


async def login(is_unify_os: bool, controller: str, port: int, ssl: bool,
                username: str, password: str) -> dict:
    logging.debug(f'login on controller {controller}')

    auth_data = {
        'username': username,
        'password': password,
    }

    try:
        uri = '/api/auth/login' if is_unify_os else '/api/login'
        async with aiohttp.ClientSession(connector=get_connector()) as session:
            async with session.post(
                f'https://{controller}:{port}{uri}',
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


async def detect_if_unify_os(controller: str, port: int,
                             ssl: bool) -> bool:
    try:
        async with aiohttp.ClientSession(connector=get_connector()) as session:
            async with session.head(
                    f'https://{controller}:{port}',
                    ssl=ssl) as resp:
                if resp.status == 200:
                    logging.debug(f'UniFi OS controller; {controller}')
                    return True
                if resp.status == 302:
                    logging.debug(f'UniFi Standard controller; {controller}')
                    return False
    except Exception:
        pass
    logging.warning(
        f'Unable to determine controller type; '
        f'Using Standard controller; {controller}')
    return False


async def get_session(asset: Asset, asset_config: dict,
                      check_config: dict) -> Tuple[dict, bool]:

    controller = check_config.get('controller')
    if controller is None:
        msg = 'missing controller in collector configuration'
        raise CheckException(msg)

    port = check_config.get('port', 443)
    ssl = check_config.get('ssl', False)
    username = asset_config.get('username')
    password = asset_config.get('password')
    if username is None or password is None:
        logging.error(f'missing credentials for {asset}')
        raise IgnoreResultException

    # we use everything what identifies a connection for an asset as key
    # of the cached 'connection'
    connection_args = (controller, port, ssl, username, password)
    prev = ConnectionCache.get_value(connection_args)
    if prev:
        return prev

    is_unify_os = await detect_if_unify_os(controller, port, ssl)

    try:
        session = await login(is_unify_os, *connection_args)
    except ConnectionError:
        raise CheckException('unable to connect')
    except Exception:
        raise
    else:
        # when connection is older than 3600 we request new 'connection'
        max_age = 3600
        ConnectionCache.set_value(
            connection_args,
            (session, is_unify_os),
            max_age)
    return session, is_unify_os
