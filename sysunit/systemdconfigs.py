import os
import copy
import typing
from configparser import RawConfigParser


class UnitConfig(RawConfigParser):
    def __init__(self, name: str = None, extension: str = None):
        super().__init__(default_section=None, interpolation=None)
        self.optionxform = str
        self.name = name
        self.extension = extension
        self._space_around_delimiters = False
        if not 'Unit' in self.sections():
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
        if not name in self.sections():
            self.add_section(name)
        self[name]._internal = False
        self[name].update(options)

    def update_internal_section(self, name: str, **options):
        """Adds or updates a section that should be ignored by systemd
        """
        if name.startswith('x-'):
            name = name[2:]
        if not name in self.sections():
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


class ServiceConfig(UnitConfig):
    def __init__(self, name: str = None):
        super().__init__(name=name, extension='service')
        if not 'Service' in self.sections():
            self.add_section('Service')


class TimerConfig(UnitConfig):
    def __init__(self, name: str = None):
        super().__init__(name=name, extension='timer')
        if not 'Timer' in self.sections():
            self.add_section('Timer')


class PathConfig(UnitConfig):
    def __init__(self, name: str = None):
        super().__init__(name=name, extension='path')
        if not 'Path' in self.sections():
            self.add_section('Path')

class SystemUnit(object):
    def __init__(self,
                 name,
                 unit_config: typing.Optional[UnitConfig] = None,
                 unit_type: typing.Optional[str] = 'service',
                 path: str = None,
                 template: bool=False,
                 ):
        """

        **Note:**

        - If the unit type is provided as an extension in `name` then the
          parameter `unit_type` is ignored.
        - If `name` contains an "@" then the parameter `template` is ignored
          and the unit is considered a template.
        - If 'unit_config' is provided it overwrites all set attributes that
          might conflict.

        Examples:

          >>> my_new_unit = SystemUnit(name='my_unit.service')
          >>> print(my_new_unit.name)
          my_unit
          >>> print(my_new_unit.type)
          service

          >>> my_new_unit = SystemUnit(name='my_unit@.service')
          >>> print(my_new_unit.name)
          my_unit
          >>> print(my_new_unit.template)
          True

        """
        self.type = unit_type
        self.template = template
        self.name = name
        self.path = path
        self._init_config(unit_config)

    def _init_config(self, unit_config):
        _type_maps = dict(
            service = ServiceConfig,
            timer = TimerConfig,
            path = PathConfig
        )

        if unit_config is None:
            _name = self.name
            if self.template:
                _name += '@'
            self.config = _type_maps[self.type](_name)
        else:
            self.config = unit_config

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, unit_config: typing.Optional[UnitConfig]):
        if unit_config.extension:
            self.type = unit_config.extension
        if unit_config.name:
            self.name = unit_config.name
        self._config = unit_config


    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path: str):
        # TODO: check if this is a valid location for systemd unit files
        self._path = path

    @property
    def name(self):
        """Name of the unit.

        **Note:**

        There are certain rules related to the name:

        - If provided, the extension is stripped from the name and used to
          determine the type of the service.

          Examples:

          >>> my_new_unit = SystemUnit(name='my_unit.service')
          >>> print(my_new_unit.name)
          my_unit
          >>> print(my_new_unit.type)
          service

          As a consequence, only valid systemd types are accepted extension.
          For a list of valid types see:

          https://www.freedesktop.org/software/systemd/man/systemd.html#Concepts

        - If the name contains a `@` it is treated as a template. A `@` is
          accepted only at the end of the name (or before the file extension,
          if provided).

          Example:

          >>> my_new_unit = SystemUnit(name='my_unit@.service')
          >>> print(my_new_unit.name)
          my_unit
          >>> print(my_new_unit.template)
          True
          >>> my_new_unit = SystemUnit(name='my_unit.service')
          >>> print(my_new_unit.template)
          False

        """
        return self._name

    @name.setter
    def name(self, name: str):
        # fetch the unit type
        parts = name.split('.')
        assert len(parts) <= 2, '`name` can contain only a single ".",'\
                f'"{name}" is not permitted.'
        _name = parts[0]
        _type = None
        if len(parts) == 2:
            _type = parts[1]
        if _type:
            self.type = _type
        # determine if it is a template
        name_parts = _name.split('@')
        assert len(name_parts) <= 2, 'The name can only contain a'\
                f' single "@", "{name}" is not permitted.'
        _name = name_parts.pop(0)
        if len(name_parts):
            assert name_parts[0] == '', '`name` can only contain a "@" at its'\
                    ' end (or before the file extension, if provided).'\
                    f'"{name}" is thus not a valid name.'
            self.template = True
        self._name = _name

    @property
    def full_name(self):
        """Get the full name of this service unit

        Example:

        >>> my_new_unit = SystemUnit(name='my_unit@.service')
        >>> print(my_new_unit.name)
        my_unit
        >>> print(my_new_unit.full_name)
        my_unit@.service

        """
        return f'{self.name}{self._template_str}.{self.type}'

    def to_dict(self):
        """Export the configuration to a dictionary
        """
        return {sect: dict(self.config[sect])
                for sect in self.config.sections()}

        

    @property
    def type(self):
        """The type of the service unit"""
        return self._type
    
    @type.setter
    def type(self, unit_type: str):
        # TODO: make sure the type is a valid type
        self._type = unit_type
        # NOTE: to get rid off once UnitConfig drops extension
        if hasattr(self, '_config'):
            self._config.extension = self._type

    @property
    def template(self):
        """The define if the unit is a template or not"""
        if self._template:
            _marked = True
        return self._template

    @template.setter
    def template(self, template: bool):
        self._template = template
        if self._template:
            self._template_str = '@'
        else:
            self._template_str = ''

    def write(self,):
        """Write the unit out to file
        """
        self.config.write_config(path=self.path, name=self.full_name)


    def read(self,):
        """Attempt to read the configuration from file
        """
        self.config.read_config(name=self.full_name, path=self.path)
