from libprobe.probe import Probe
from lib.check.unifiguest import check_unifiguest
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = {
        'unifiguest': check_unifiguest,
    }

    probe = Probe('unifiguest', version, checks)
    probe.start()
