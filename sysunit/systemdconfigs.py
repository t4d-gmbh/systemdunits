import os
import copy
import typing
import warnings
from types import SimpleNamespace

from .unit_configs import (
        UnitConfig,
        TargetConfig,
        ServiceConfig,
        TimerConfig,
        PathConfig
    )
from .utils import noglobals
from .commands import _Run


class SystemUnit(object):
    def __init__(self,
                 name,
                 unit_config: typing.Optional[UnitConfig] = None,
                 type: typing.Optional[str] = 'service',
                 path: str = '~/.config/systemd/user',
                 template: bool = False,
                 manager: str = '--user'
                 ):
        """

        **Note:**

        - If you use `{...}` in the `name` then the unit is considered a
          batch of units and all the option values are formatted
          when writing the unit to a file. As a consequence **you need to**
          **escape all `{` and `}` that should not be formatted!**
          Hint: replace for example `"${HOME}"` with `"${{HOME}}"`.
        - If the unit type is provided as an extension in `name` then the
          parameter `type` is ignored.
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
        self.type = type
        self.template = template
        self.name = name
        self.path = path
        self._init_config(unit_config)
        self._init_batch_vars()
        self.run = _Run(self, manager)

    def _init_config(self, unit_config):
        _type_maps = dict(
            target=TargetConfig,
            service=ServiceConfig,
            timer=TimerConfig,
            path=PathConfig
        )

        if unit_config is None:
            # ###
            # NOTE: to get rid of once UnitConfig drops name
            _name = self.name
            if self.template:
                _name += '@'
            # ###
            self.config = _type_maps[self.type](_name)
        else:
            self.config = unit_config

    def set(self, section, option, value, multioption=False):
        """Set the value of an option in a section"""
        return self.config.set(section, option, value, multioption)

    def append(self, section, option, value, multioption=False):
        """Append other value to an option in a section"""
        return self.config.append(section, option, value)

    def _init_batch_vars(self,):
        self.batch_vars = SimpleNamespace()

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
        """The path where the unit is, or should be, written.

        You might use `'~'` in the path, it will be replaced by the user's
        home directory, so the path `'~/.config/systemd/user'` is a valid path.
        """
        return os.path.expanduser(self._path)

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
        self._batched = False
        if '{' in self._name and '}' in self._name:
            self._batched = True

    @property
    def is_batched(self):
        return self._batched

    @property
    def existing(self):
        """List units for which a file exists

        **Note:**

        This method does not compare if the configuration of the existing file
        matched.

        See `exists` for an example
        """
        assert self._batched, 'This method is only allowed for batched units'
        return [name
                for name in self.expanded_names()
                if os.path.exists(self._filename(name))]

    @property
    def exists(self):
        """Is the unit already written to disk

        **Note:**

        This method does not compare if the configuration of the existing file
        matched.

        Examples:
        ---------
        >>> my_unit = SystemUnit(name='test_unit.service')
        >>> my_unit.exists
        False
        >>> my_unit.write()
        >>> my_unit.exists
        True
        >>> my_unit.remove()
        >>> my_unit.exists
        False

        For batched units it check if all files exists

        >>> my_unit = SystemUnit(name='test_unit-{case}.service')
        >>> my_unit.batch_vars.case = [1,2,3]
        >>> my_unit.exists
        False
        >>> my_unit.write()
        >>> my_unit.exists
        True
        >>> my_unit_case_2 = SystemUnit(name='test_unit-2.service')
        >>> my_unit_case_2.exists
        True
        >>> my_unit_case_2.remove()
        >>> my_unit_case_2.exists
        False
        >>> my_unit.exists  # case=2 is missing now
        False
        >>> my_unit.existing
        ['test_unit-1.service', 'test_unit-3.service']
        >>> my_unit.remove()
        >>> my_unit.exists
        False
        """
        return all((os.path.exists(self._filename(name))
                    for name in self.expanded_names()))

    def _filename(self, name):
        return os.path.join(self.path, name)

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
        return self._full_name(self.name)

    def expanded_name(self,
                      instance: typing.Optional[str] = None,
                      **batch_kws):
        """Get the fully formatted name of a unit or instance

        If the unit is a template then you might specify a particular instance.

        If the unit is batched the you can provide a particular batch value.
        In this case the values present in `self.batch_vars` are ignored and
        the name is rendered with the provided values. If you want the get the
        names formatted with the values saved, use `expanded_names` instead.

        Examples:
        ---------

        >>> my_unit = SystemUnit(name='my_unit-{tag}@.service')
        >>> my_unit.full_name
        'my_unit-{tag}@.service'
        >>> my_unit.expanded_name()
        'my_unit-{tag}@.service'
        >>> my_unit.expanded_name(instance='bla')
        'my_unit-{tag}@bla.service'
        >>> my_unit.expanded_name(instance='bla', tag='test')
        'my_unit-test@bla.service'
        """
        if batch_kws:
            name = self._formatted_name(**batch_kws)
        else:
            name = self.name
        return self._full_name(name, instance)

    def expanded_names(self,
                       instance: typing.Optional[str] = None,
                       ):
        """Get a list of all unit names.

        **Note:**
        If the unit is not batched (see ... for further details) then a list
        containing only the full name of the unit is returned.

        Example:

        >>> my_unit_batch = SystemUnit(name='my_unit-{custom}.service')
        >>> my_unit_batch.batch_vars.custom = ['bla', 'blu']
        >>> my_unit_batch.full_name
        'my_unit-{custom}.service'
        >>> for unit_name in my_unit_batch.expanded_names():
        ...     unit_name
        'my_unit-bla.service'
        'my_unit-blu.service'

        You can get names of a particular instance if the unit is templated:

        >>> my_unit_batch = SystemUnit(name='my_unit@.service')
        >>> my_unit_batch.full_name
        'my_unit@.service'
        >>> for unit_name in my_unit_batch.expanded_names(instance='hello'):
        ...     unit_name
        'my_unit@hello.service'
        """
        if not self._batched:
            return [self.expanded_name(instance=instance), ]
        else:
            names = []
            batched_variables = self._get_batched_vars()
            nbr_values = len(next(iter(batched_variables.values())))
            for i in range(nbr_values):
                _variables = {k: v[i] for k, v in batched_variables.items()}
                names.append(
                    self._full_name(self._formatted_name(**_variables),
                                    instance)
                )
            return names

    def _full_name(self, name, instance: typing.Optional[str] = None):
        if instance is None:
            instance = ''
        return f'{name}{self._template_str}{instance}.{self.type}'

    def to_dict(self):
        """Export the configuration to a dictionary
        """
        return {sect: dict(self.config[sect])
                for sect in self.config.sections()}

    def from_dict(self, unit_dict: dict):
        """Load a configuration from a dictionary

        Parameters:
        -----------
        :param: unit_dict
           a dictionary holding for each section a dictionary with options.

           **Note:**

           If the values in the options dictionary are of type tuple, then the
           2nd element must be a boolean indicating whether or not the option
           should be considered as a multi-option.
           Multi-options have a list as value and lead to a separate line for
           each element with repeated option name, when writing to an unit
           file.
        """
        for service, options in unit_dict.items():
            if service not in self.config.sections():
                self.config.add_section(service)
            for name, value in options.items():
                if not isinstance(value, tuple):
                    _value = (value, False)
                else:
                    _value = value
                self.set(service, name, *_value)

    @property
    def type(self):
        """The type of the service unit"""
        return self._type

    @type.setter
    def type(self, type: str):
        # TODO: make sure the type is a valid type
        self._type = type
        # NOTE: to get rid of once UnitConfig drops extension
        if hasattr(self, '_config'):
            self._config.extension = self._type

    @property
    def template(self):
        """The define if the unit is a template or not"""
        return self._template

    @template.setter
    def template(self, template: bool):
        self._template = template
        if self._template:
            self._template_str = '@'
        else:
            self._template_str = ''

    def write(self):
        """Write the unit out to file
        """
        if self._batched:
            self._write_batch()
        else:
            self._write(config=self.config,
                        path=self.path,
                        name=self.full_name)

    def _write(self, config, name, path):
        config.write_config(path=path, name=name)

    def _write_batch(self):
        for name, config in self.batched_configs:
            self._write(config=config, path=self.path, name=name)

    @property
    def batched_configs(self):
        """Generator for looping over units (name, config) in a batched unit

        Example:
        >>> my_unit = SystemUnit(name='my_unit-{custom}.service')
        >>> my_unit.from_dict(
        ...     dict(Unit=dict(Description='something {custom}'))
        ... )
        >>> print(my_unit.to_dict())
        {'Unit': {'Description': 'something {custom}'}, 'Service': {}}
        >>> my_unit.batch_vars.custom = ['bla', 'blu', 'bli']
        >>> for name, config in my_unit.batched_configs:
        ...     print(name)
        ...     print(config.to_dict())
        my_unit-bla.service
        {'Unit': {'Description': 'something bla'}, 'Service': {}}
        my_unit-blu.service
        {'Unit': {'Description': 'something blu'}, 'Service': {}}
        my_unit-bli.service
        {'Unit': {'Description': 'something bli'}, 'Service': {}}
        """
        batched_variables = self._get_batched_vars()
        nbr_values = len(next(iter(batched_variables.values())))
        # for each name create a new config {name: config, ...}
        for i in range(nbr_values):
            _variables = {k: v[i] for k, v in batched_variables.items()}
            new_config = copy.deepcopy(self.config)
            name = self._full_name(self._formatted_name(**_variables))
            config = self._formatted_config(new_config, **_variables)
            yield name, config

    def _get_batched_vars(self):
        assert vars(self.batch_vars), "Missing batch variables.\nDid you"\
                " forget to specify your batch variables in"\
                " `self.batch_vars?"
        return vars(self.batch_vars)

    @noglobals
    def _formatted_name(self, **variables):
        return self.name.format(**variables)

    # @noglobals
    # def _formatted_instance_name(self,
    #                              instance: typing.Optional[str],
    #                              **variables):
    #     return self._full_name(self.name.format(**variables),
    #                            instance=instance)

    @noglobals
    def _formatted_config(self, new_config, **variables):
        return self.config.formatted(new_config, **variables)

    def read(self,):
        """Attempt to read the configuration from file
        """
        self.config.read_config(name=self.full_name, path=self.path)

    def remove(self):
        """Remove unit files from disk.
        """
        # TODO: allow removal of single unit if it is _batched
        for name in self.expanded_names():
            try:
                os.remove(os.path.join(self.path, name))
            except FileNotFoundError:
                warnings.warn(f'No unit matching the name {name} to remove at'
                              f'{self.path}', Warning)
