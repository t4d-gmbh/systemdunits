"""Small package to write unit files for systemd.

.. moduleauthor:: Jonas Liechti

"""
from .configs import MultiConfigParser
from .systemdconfigs import SystemUnit


__all__ = [
    'SystemUnit', 'MultiConfigParser'
]


def load_tests(loader, tests, ignore):
    import doctest

    tests.addTests(doctest.DocTestSuite(systemdconfigs))
    tests.addTests(doctest.DocTestSuite(commands))
    return tests
