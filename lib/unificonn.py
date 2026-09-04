import aiohttp
import logging
from urllib.parse import urlparse, urljoin
from http.cookies import SimpleCookie
from libprobe.asset import Asset
from libprobe.exceptions import CheckException
from lib.connection_cache import ConnectionCache, TCredentials
from .connector import get_connector
from . import DOCS_URL


async def login(address: str,
                port: int,
                ssl: bool,
                username: str,
                password: str) -> TCredentials:
    auth_payload = {"username": username, "password": password}
    candidate_ports = [port]

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession(connector=get_connector()) as session:
        for current_port in candidate_ports:
            base_url = f"https://{address}:{current_port}"

            test_endpoints = [
                {"is_os": True, "path": "/api/auth/login"},
                {"is_os": True, "path": "/proxy/network/api/auth/login"},
                {"is_os": False, "path": "/api/login"},
            ]

            for attempt in test_endpoints:
                url = f"{base_url}{attempt['path']}"

                try:
                    async with session.post(
                        url,
                        json=auth_payload,
                        headers=headers,
                        ssl=ssl,
                        allow_redirects=False
                    ) as resp:

                        # Handle 302 redirects to alternate ports
                        if resp.status in (301, 302, 307, 308):
                            location = resp.headers.get("Location")
                            if location:
                                absolute_redirect = urljoin(url, location)
                                parsed = urlparse(absolute_redirect)

                                if parsed.port and \
                                        parsed.port not in candidate_ports:
                                    candidate_ports.append(parsed.port)
                            continue

                        content_type = resp.headers.get("Content-Type", "")
                        if "text/html" in content_type:
                            continue

                        if resp.status == 200:
                            cookies = {}

                            # Extract from resp.cookies
                            for key, cookie in resp.cookies.items():
                                cookies[key] = cookie.value

                            # Extract from cookie_jar
                            filtered_cookies = \
                                session.cookie_jar.filter_cookies(resp.url)
                            for key, cookie in filtered_cookies.items():
                                cookies[key] = cookie.value

                            # Extract from raw Set-Cookie headers
                            if not cookies:
                                for header_val in resp.headers.getall(
                                        'Set-Cookie',
                                        []):
                                    simple_cookie = SimpleCookie()
                                    simple_cookie.load(header_val)
                                    for k, v in simple_cookie.items():
                                        cookies[k] = v.value

                            csrf_token = resp.headers.get("x-csrf-token") or \
                                resp.headers.get("X-CSRF-Token")

                            if cookies or "application/json" in content_type:
                                logging.debug(
                                    f"Authenticated successfully on {url} "
                                    f"(is_unifi_os={attempt['is_os']}, "
                                    f"base_url={base_url})"
                                )
                                headers = {
                                    "Accept": "application/json",
                                }
                                if csrf_token:
                                    headers["X-CSRF-Token"] = csrf_token

                                return {
                                    "base_url": base_url,
                                    "is_unifi_os": attempt["is_os"],
                                    "cookies": cookies,
                                    "headers": headers,
                                }

                except Exception as e:
                    logging.debug(f"Exception trying {url}: {e}")

    raise Exception(
        "Unable to authenticate with UniFi Controller at "
        f"https://{address}:{port}")


async def get_credentials(asset: Asset, local_config: dict,
                          config: dict) -> TCredentials:

    controller = config.get('controller')
    if not controller:
        msg = 'missing or empty controller in collector configuration'
        raise CheckException(msg)
    port = config.get('port', 443)
    ssl = config.get('ssl', False)
    username = local_config.get('username')
    password = local_config.get('password')
    if username is None or password is None:
        raise CheckException(
            'Missing credentials. Please refer to the following documentation'
            f' for detailed instructions: <{DOCS_URL}>'
        )

    # we use everything what identifies a connection for an asset as key
    # of the cached 'connection'
    connection_args = (controller, port, ssl, username, password)
    prev = ConnectionCache.get_value(connection_args)
    if prev:
        return prev

    try:
        credentials = await login(*connection_args)
    except ConnectionError:
        raise CheckException('unable to connect')
    except Exception:
        raise
    else:
        # when connection is older than 3600 we request new 'connection'
        max_age = 3600
        ConnectionCache.set_value(
            connection_args,
            credentials,
            max_age)
    return credentials


async def sanity_check(resp: aiohttp.ClientResponse, url: str):
    content_type = resp.headers.get('Content-Type', '')
    if 'application/json' not in content_type:
        raw_text = await resp.text()
        raise ValueError(
            f"Expected JSON from {url}, "
            f"but received {content_type}: {raw_text[:200]}")

    try:
        resp.raise_for_status()
    except aiohttp.ClientResponseError as e:
        msg = None
        try:
            data = await resp.json()
            if isinstance(data, dict):
                # Check UniFi meta msg pattern
                meta = data.get('meta')
                if isinstance(meta, dict):
                    msg = meta.get('msg')

                # Fallback for UniFi OS / standard API responses
                if not msg:
                    msg = data.get('message')
        except Exception:
            # If JSON parsing fails during error handling,
            # fall back to the original exception
            pass

        if msg:
            msg = f"{msg} ({e.status} {e.message}, url='{url}')"
            raise CheckException(msg) from e

        raise e
