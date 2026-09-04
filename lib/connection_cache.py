import time
from typing import TypedDict


class TCredentials(TypedDict):
    base_url: str
    is_unifi_os: bool
    cookies: dict[str, str]
    headers: dict[str, str]


K = tuple[str, int, bool, str, str]


class ConnectionCache:
    _all = {}

    @classmethod
    def get_value(cls, key: K) -> TCredentials | None:
        if key in cls._all:
            val, expire_ts = cls._all[key]
            expired = expire_ts and expire_ts < time.time()
            if expired:
                del cls._all[key]
            else:
                return val
        return None

    @classmethod
    def set_value(cls, key: K, val: TCredentials, max_age: int | None = None):
        expire_ts = time.time() + max_age if max_age else None
        cls._all[key] = (val, expire_ts)
