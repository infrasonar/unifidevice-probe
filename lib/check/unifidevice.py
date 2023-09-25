import aiohttp
import logging
from urllib.parse import quote
from libprobe.asset import Asset
from libprobe.exceptions import IncompleteResultException
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


def to_float(val):
    if val is None:
        return
    return float(val)


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
            to_int(stat.get(f'{radio["name"]}-mac_filter_rejections')),  # int
            'rx_bytes': to_int(stat.get(f'{radio["name"]}-rx_bytes')),  # int
            'rx_crypts': to_int(stat.get(f'{radio["name"]}-rx_crypts')),  # int
            'rx_dropped':
            to_int(stat.get(f'{radio["name"]}-rx_dropped')),  # int
            'rx_errors': to_int(stat.get(f'{radio["name"]}-rx_errors')),  # int
            'rx_frags': to_int(stat.get(f'{radio["name"]}-rx_frags')),  # int
            'tx_bytes': to_int(stat.get(f'{radio["name"]}-tx_bytes')),  # int
            'tx_dropped':
            to_int(stat.get(f'{radio["name"]}-tx_dropped')),  # int
            'tx_errors': to_int(stat.get(f'{radio["name"]}-tx_errors')),  # int
            'tx_packets':
            to_int(stat.get(f'{radio["name"]}-tx_packets')),  # int
            'tx_power': radio.get('tx_power'),  # int
            'tx_retries': radio.get('tx_retries'),  # int
        }
        for radio in device['radio_table_stats'] if radio.get('name')
    ]
    radio_complete = len(radio) == len(device['radio_table_stats'])

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
            'tx_bytes': vap.get('tx_bytes'),  # int
            'tx_dropped': vap.get('tx_dropped'),  # int
            'tx_errors': vap.get('tx_errors'),  # int
            'tx_power': vap.get('tx_power'),  # int
        }
        for vap in device['vap_table'] if 'name' if vap.get('name')
    ]
    vap_complete = len(vap) == len(device['vap_table'])

    item = {
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
        'cpu': to_float(device.get('system-stats', {}).get('cpu')),
        'mem': to_float(device.get('system-stats', {}).get('mem')),
    }

    state = {
        'device': [item],
        'radio': radio,
        'vap': vap,
    }
    if not radio_complete:
        raise IncompleteResultException('At least one radio without a name',
                                        result=state)
    if not vap_complete:
        raise IncompleteResultException('At least one VAP without a name',
                                        result=state)
    return state
