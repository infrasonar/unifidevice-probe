import aiohttp
import logging
from urllib.parse import quote
from libprobe.asset import Asset
from libprobe.exceptions import IgnoreResultException
from lib.unificonn import get_session


DEVICE_STATE = {
    0: 'offline',
    1: 'connected',
    2: 'pending adoption',
    4: 'updating',
    5: 'provisioning',
    6: 'unreachable',
    7: 'adopting',
    8: 'deleting',
    9: 'adoption error',
    10: 'adoption failed',
    11: 'isolated',
}


def to_int(val):
    if val is None:
        return
    return int(val)


async def check_unifidevice(
    asset: Asset,
    asset_config: dict,
    check_config: dict
) -> dict:
    site = check_config.get('site', 'default')
    ssl = check_config.get('ssl', False)
    mac = check_config.get('mac')
    if mac in (None, ''):
        logging.error(f'missing mac address for {asset}')
        raise IgnoreResultException
    if mac.startswith('?'):
        logging.error(f'invalid mac address for {asset}')
        raise IgnoreResultException

    url = f'/api/s/{quote(site, safe="")}/stat/device/{quote(mac, safe="")}'
    session = await get_session(asset, asset_config, check_config)
    async with aiohttp.ClientSession(**session) as session:
        async with session.get(url, ssl=ssl) as resp:
            resp.raise_for_status()
            data = await resp.json()
            assert len(data['data']), 'device not not found'

    device = data['data'][0]
    stat = device['stat']['ap']

    # same metrics is are available in the vap_table but with (most likely)
    # aggregated values
    radio = [
        {
            'name': radio['name'],  # str
            'cu_self_rx': radio.get('cu_self_rx'),  # int
            'cu_self_tx': radio.get('cu_self_tx'),  # int
            'cu_total': radio.get('cu_total'),  # int
            'radio': radio.get('radio'),  # str
            'mac_filter_rejections':
                int(stat.get(f'{radio["name"]}-mac_filter_rejections')),  # int
            'rx_crypts': int(stat.get(f'{radio["name"]}-rx_crypts')),  # int
            'rx_dropped': int(stat.get(f'{radio["name"]}-rx_dropped')),  # int
            'rx_errors': int(stat.get(f'{radio["name"]}-rx_errors')),  # int
            'rx_frags': int(stat.get(f'{radio["name"]}-rx_frags')),  # int
            'tx_bytes': int(stat.get(f'{radio["name"]}-tx_bytes')),  # int
            'tx_dropped': int(stat.get(f'{radio["name"]}-tx_dropped')),  # int
            'tx_errors': int(stat.get(f'{radio["name"]}-tx_errors')),  # int
            'tx_packets': int(stat.get(f'{radio["name"]}-tx_packets')),  # int
            'tx_retries': int(stat.get(f'{radio["name"]}-tx_retries')),  # int
        }
        for radio in device['radio_table_stats']
    ]

    vap = [
        {
            'name': vap['name'],  # str
            'bssid': vap.get('bssid'),  # str
            'channel': vap.get('channel'),  # int
            'essid': vap.get('essid'),  # str
            'extchannel': vap.get('extchannel'),  # int/optional
            'num_sta': vap.get('num_sta'),  # int
            'radio_name': vap.get('radio_name'),  # str + ref
            'rx_bytes': vap.get('rx_bytes'),  # int
            'rx_crypts': vap.get('rx_crypts'),  # int
            'rx_dropped': vap.get('rx_dropped'),  # int
            'rx_errors': vap.get('rx_errors'),  # int
            'rx_frags': vap.get('rx_frags'),  # int
        }
        for vap in device['vap_table']
    ]

    device = [{
        'name': device['name'],  # str
        'mac': device.get('mac'),  # str
        'state': DEVICE_STATE.get(device.get('state')),  # str
        'adopted': device.get('adopted'),  # bool
        'type': device.get('type'),  # str
        'model': device.get('model'),  # str
        'ip': device.get('ip'),  # str
        'isolated': device.get('isolated'),  # bool
        'uplink': device.get('uplink', {}).get('name'),  # str
        'version': device.get('version'),  # str
        'uptime': device.get('uptime'),  # int
    }]

    return {
        'device': device,
        'radio': radio,
        'vap': vap,
    }