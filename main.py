from libprobe.probe import Probe
from lib.check.unifidevice import CheckUnifiDevice
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = (
        CheckUnifiDevice,
    )

    probe = Probe('unifidevice', version, checks)
    probe.start()
