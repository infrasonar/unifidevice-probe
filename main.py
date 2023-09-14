from libprobe.probe import Probe
from lib.check.system import check_system
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = {
        'system': check_system,
    }

    probe = Probe('unifiguest', version, checks)
    probe.start()
