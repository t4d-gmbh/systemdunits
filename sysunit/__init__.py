"""Small package to write unit files for systemd.

.. moduleauthor:: Jonas Liechti

"""
import doctest

from .custom import MultiConfigParser
from .systemdconfigs import SystemUnit, TimerConfig


__all__ = [
    'SystemUnit', 'TimerConfig'
]

def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(systemdconfigs))
    return tests
