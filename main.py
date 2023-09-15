from libprobe.probe import Probe
from lib.check.unifidevice import check_unifidevice
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = {
        'unifidevice': check_unifidevice,
    }

    probe = Probe('unifidevice', version, checks)
    probe.start()
