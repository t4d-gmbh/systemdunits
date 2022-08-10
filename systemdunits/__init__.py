"""Small package to write unit files for systemd.

.. moduleauthor:: Jonas Liechti

"""

from .systemdconfigs import SystemdUnit, TimerUnit


__all__ = [
    'SystemdGenuineUnit',
    'TimerUnit'
]
