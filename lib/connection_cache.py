import time
from typing import Any

K = tuple[str, int, bool, str, str]
V = tuple[dict[str, Any], bool]  # session, is_unifi_os


class ConnectionCache:
    _all = {}

    @classmethod
    def get_value(cls, key: K) -> V | None:
        if key in cls._all:
            val, expire_ts = cls._all[key]
            expired = expire_ts and expire_ts < time.time()
            if expired:
                del cls._all[key]
            else:
                return val
        return None

    @classmethod
    def set_value(cls, key: K, val: V, max_age: int | None = None):
        expire_ts = time.time() + max_age if max_age else None
        cls._all[key] = (val, expire_ts)
