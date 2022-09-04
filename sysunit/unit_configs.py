import os
import copy
from collections import OrderedDict

from .utils import noglobals
from .configs import MultiConfigParser


class UnitConfig(MultiConfigParser):
    def __init__(self, name: str = None, extension: str = None):
        super().__init__(default_section=None,
                         interpolation=None,
                         dict_type=OrderedDict,
                         strict=False
                         )
        self.optionxform = str
        self.name = name
        self.extension = extension
        self._space_around_delimiters = False
        if 'Unit' not in self.sections():
            self.add_section('Unit')

    def write_config(self, path: str, name: str = None):
        """Write the config to a file
        """
        if not name:
            raise ValueError('You need to provide a valid name for the unit'
                             f' file. "{name}" is not a valid name')
        if self.extension and not name.endswith(self.extension):
            name += f".{self.extension}"

        export_u = self._externalise_internals()

        with open(os.path.join(path, name), 'w') as unitfobj:
            export_u.write(
                unitfobj,
                space_around_delimiters=self._space_around_delimiters
            )
        del export_u

    def to_dict(self):
        """Export the configuration to a dictionary
        """
        return {sect: dict(self[sect])
                for sect in self.sections()}

    def _externalise_internals(self,):
        external_u = copy.copy(self)
        for section in external_u.sections():
            if self.is_internal(section):
                ext_sect = f"x-{section}"
                external_u.add_section(ext_sect)
                for item in external_u.items(section):
                    external_u.set(ext_sect, item[0], item[1])
                external_u.remove_section(section)
        return external_u

    def _internalise_internals(self,):
        internal_u = copy.copy(self)
        for section in internal_u.sections():
            if section.startswith('x-'):
                int_sect = section[2:]
                internal_u.add_section(int_sect)
                for item in internal_u.items(section):
                    internal_u.set(int_sect, item[0], item[1])
                internal_u.remove_section(section)
                internal_u.set_internal(int_sect)
        return internal_u

    def set_internal(self, section):
        """Set a section to internal (i.e. will be ignored by systemd)
        """
        self[section]._internal = True

    def set_external(self, section):
        """Set a section to external (i.e. will be read by systemd)

        .. note::

          By default all sections are considered external, unless their name
          start with `x-'.
        """
        self[section]._internal = False

    def is_internal(self, section):
        """Check if a section is internal or not.

        .. note::

          It is not tested if a section does really exist. Non-existing
          sections are not considered internal.
        """
        if getattr(self[section], '_internal', None):
            return True
        else:
            return False

    def read_config(self, name: str, path: str = None):
        """Read a systemd unit file
        """
        if path is not None:
            filename = os.path.join(path, name)
        else:
            filename = name

        self.read(filename)
        self = self._internalise_internals()

    def update_section(self, name: str, **options):
        """Adds or updates a section to the unit that is relevant for systemd

        .. note::

          If you want to add a section that should be ignored by systemd, use
          the `update_internal_section` method instead.

        """
        if name not in self.sections():
            self.add_section(name)
        self[name]._internal = False
        self[name].update(options)

    def update_internal_section(self, name: str, **options):
        """Adds or updates a section that should be ignored by systemd
        """
        if name.startswith('x-'):
            name = name[2:]
        if name not in self.sections():
            self.add_section(name)
        self[name]._internal = True
        self[name].update({k: str(v) for k, v in options.items()})

    def pop_section(self, name: str):
        """Return and remove a section from the configuration.

        **Note:**

        Only the content of the section is returned and **not** the section
        object itself.
        """
        section = {item for item in self.items(name)}
        self.remove_section(name)
        return section

    @noglobals
    def formatted(self, new_config, **variables):
        """Return a copy of this instance with formatted values of the options
        """
        for section in new_config.sections():
            for name, value in new_config.items(section):
                _multiopt = False
                if (section, name) in self._multioptions:
                    _multiopt = True
                    value_formatted = [val.format(**variables)
                                       for val in value]
                else:
                    try:
                        value_formatted = value.format(**variables)
                    except AttributeError:
                        value_formatted = [val.format(**variables)
                                           for val in value]
                new_config.set(
                    section,
                    name,
                    value_formatted,
                    multioption=_multiopt
                )
        return new_config


class TargetConfig(UnitConfig):
    def __init__(self, name: str = None):
        super().__init__(name=name, extension='target')


class ServiceConfig(UnitConfig):
    def __init__(self, name: str = None):
        super().__init__(name=name, extension='service')
        if 'Service' not in self.sections():
            self.add_section('Service')


class TimerConfig(UnitConfig):
    def __init__(self, name: str = None):
        super().__init__(name=name, extension='timer')
        if 'Timer' not in self.sections():
            self.add_section('Timer')


class PathConfig(UnitConfig):
    def __init__(self, name: str = None):
        super().__init__(name=name, extension='path')
        if 'Path' not in self.sections():
            self.add_section('Path')
