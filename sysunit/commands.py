import typing
import asyncio

from types import SimpleNamespace


class _Run:
    """Defines a set of methods that run systemd commands.

    Examples:
    ---------

    >>> from sysunit import SystemUnit
    >>> my_unit = SystemUnit(
    ...        'test-unit-run',
    ...         type='target',
    ...         manager='--user'
    ...     )
    >>> my_unit.from_dict(
    ...     dict(
    ...         Unit=dict(Description='From a test on _Run'),
    ...         Install=dict(WantedBy='multi-user.target')
    ...     )
    ... )
    >>> my_unit.write()
    >>> asyncio.run(my_unit.run.daemon_reload())
    ('', '')
    >>> asyncio.run(my_unit.run.start())
    ('', '')
    >>> out, err = asyncio.run(my_unit.run.status())
    >>> err
    ''
    >>> print(out)  # doctest:+ELLIPSIS
    ...             # doctest:+NORMALIZE_WHITESPACE
    ● test-unit-run.target - From a test on _Run
    Loaded: loaded (.../.config/systemd/user/test-unit-run.target; disabled;
            vendor preset: enabled)
    Active: active since ... ago
    ... systemd[...]: Reached target From a test on _Run.

    >>> out, err = asyncio.run(my_unit.run.enable())
    >>> out
    ''
    >>> print(err)  # doctest:+ELLIPSIS
    ...             # doctest:+NORMALIZE_WHITESPACE
    Created symlink
    .../.config/systemd/user/multi-user.target.wants/test-unit-run.target →
    .../.config/systemd/user/test-unit-run.target.
    >>> out, err = asyncio.run(my_unit.run.status())
    >>> err
    ''
    >>> print(out)  # doctest:+ELLIPSIS
    ...             # doctest:+NORMALIZE_WHITESPACE
    ● test-unit-run.target - From a test on _Run
    Loaded: loaded (.../.config/systemd/user/test-unit-run.target; enabled;
    vendor preset: enabled)
    Active: active since ... ago
    ... systemd[...]: Reached target From a test on _Run.
    >>> out, err = asyncio.run(my_unit.run.disable())
    >>> out
    ''
    >>> print(err)  # doctest:+ELLIPSIS
    ...             # doctest:+NORMALIZE_WHITESPACE
    Removed
    .../.config/systemd/user/multi-user.target.wants/test-unit-run.target.
    >>> out, err = asyncio.run(my_unit.run.status())
    >>> err
    ''
    >>> print(out)  # doctest:+ELLIPSIS
    ...             # doctest:+NORMALIZE_WHITESPACE
    ● test-unit-run.target - From a test on _Run
    Loaded: loaded (.../.config/systemd/user/test-unit-run.target; disabled;
    vendor preset: enabled)
    Active: active since ... ago
    ... systemd[...]: Reached target From a test on _Run.
    >>> asyncio.run(my_unit.run.stop())
    ('', '')
    >>> out, err = asyncio.run(my_unit.run.status())
    >>> err
    ''
    >>> print(out)  # doctest:+ELLIPSIS
    ...             # doctest:+NORMALIZE_WHITESPACE
    ● test-unit-run.target - From a test on _Run
    Loaded: loaded (.../.config/systemd/user/test-unit-run.target; disabled;
    vendor preset: enabled)
    Active: inactive (dead)
    ...
    >>> my_unit.remove()
    """
    def __init__(self, sysunit, manager: str = '--user'):
        self.sysunit = sysunit
        # TODO: store the last status here (or store in SysUnit?)
        self.last = SimpleNamespace
        assert manager in ['--user', '--system']
        self.manager = manager

    async def async_systemctl(self,
                              unit: str,
                              command: str,
                              env: dict = dict(),
                              stdout=asyncio.subprocess.PIPE,
                              stderr=asyncio.subprocess.PIPE,
                              encoding='utf-8'
                              ):
        """Run systemctl command asynchronously

        Returns:

        stdout, stderr
        """
        args = ['systemctl', self.manager, command]
        if unit:
            args.append(unit)
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=stdout, stderr=stderr
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode(encoding), stderr.decode(encoding)

    async def _unit_cmd(self, command, instance, env):
        if self.sysunit.is_batched:
            stdout, stderr = {}, {}
            for name in self.sysunit.expanded_names(instance=instance):
                _stdout, _stderr = await self.async_systemctl(
                        name, command, env=env)
                stdout[name] = _stdout
                stderr[name] = _stderr
        else:
            stdout, stderr = await self.async_systemctl(
                    self.sysunit.expanded_name(instance), command, env=env)
        return stdout, stderr

    async def status(self, instance: typing.Optional[str] = None,
                     env: typing.Optional[dict] = None):
        """Get the status of the service

        Example:
        --------
        >>> from sysunit import SystemUnit
        >>> my_unit = SystemUnit(name='test_unit-{custom}@',
        ...                      type='target')
        >>> my_unit.path='~/.config/systemd/user'
        >>> my_unit.batch_vars.custom = ['bla', 'bli']
        >>> config_data = dict(
        ...     Unit=dict(
        ...         Description='this is "{custom}" dummy target',
        ...         After='multi-user.target',
        ...     ),
        ...     Install=dict(
        ...        WantedBy='multi-user.target',
        ...        )
        ...     )
        >>> my_unit.from_dict(config_data)
        >>> my_unit.write()
        >>> import asyncio
        >>> stdout, stderr = asyncio.run(my_unit.run.status('1'))
        >>> for name in stdout:
        ...     print(name)
        ...     print('-')
        ...     print(stdout[name])
        ...     print('-')
        ...     print(stderr[name])
        ...     print('---')  # doctest:+ELLIPSIS
        ...                   # doctest:+NORMALIZE_WHITESPACE
        test_unit-bla@1.target
        -
        ● test_unit-bla@1.target - this is "bla" dummy target
             Loaded: loaded (.../.config/systemd/user/test_unit-bla@.target;
                     disabled; vendor preset: enabled)
             Active: inactive (dead)
        <BLANKLINE>
        -
        <BLANKLINE>
        ---
        test_unit-bli@1.target
        -
        ● test_unit-bli@1.target - this is "bli" dummy target
             Loaded: loaded (.../.config/systemd/user/test_unit-bli@.target;
                     disabled; vendor preset: enabled)
             Active: inactive (dead)
        <BLANKLINE>
        -
        <BLANKLINE>
        ---
        >>> my_unit.remove()
        """
        # TODO: wrap the output and update the 'last' status.
        return await self._unit_cmd('status', instance=instance, env=env)

    async def start(self,
                    instance: typing.Optional[str] = None,
                    env: typing.Optional[dict] = None):
        """Start a unit

        Example:
        --------
        >>> from sysunit import SystemUnit
        >>> my_unit = SystemUnit(name='test_unit@',
        ...                      type='target')
        >>> my_unit.path='~/.config/systemd/user'
        >>> config_data = dict(
        ...     Unit=dict(
        ...         Description='instance %i: dummy target',
        ...         After='multi-user.target',
        ...     ),
        ...     Install=dict(
        ...        WantedBy='multi-user.target',
        ...        )
        ...     )
        >>> my_unit.from_dict(config_data)
        >>> my_unit.write()
        >>> import asyncio
        >>> _ = asyncio.run(my_unit.run.daemon_reload())
        >>> stdout, stderr = asyncio.run(my_unit.run.start('1'))
        >>> print(stdout)  # doctest:+NORMALIZE_WHITESPACE
        >>> print(stderr)  # doctest:+NORMALIZE_WHITESPACE
        >>> stdout, stderr = asyncio.run(my_unit.run.status('1'))
        >>> print(stdout)  # doctest:+NORMALIZE_WHITESPACE
        ...                # doctest:+ELLIPSIS
        ● test_unit@1.target - instance 1: dummy target
             Loaded: loaded (.../.config/systemd/user/test_unit@.target;
                     disabled; vendor preset: enabled)
             Active: active since ...
        <BLANKLINE>
        ... systemd[...]: Reached target instance 1: dummy target.
        <BLANKLINE>
        >>> print(stderr)  # doctest:+NORMALIZE_WHITESPACE
        >>> stdout, stderr = asyncio.run(my_unit.run.stop('1'))
        >>> print(stdout)  # doctest:+NORMALIZE_WHITESPACE
        >>> print(stderr)  # doctest:+NORMALIZE_WHITESPACE
        >>> stdout, stderr = asyncio.run(my_unit.run.status('1'))
        >>> print(stdout)  # doctest:+NORMALIZE_WHITESPACE
        ...                # doctest:+ELLIPSIS
        ● test_unit@1.target - instance 1: dummy target
             Loaded: loaded (.../.config/systemd/user/test_unit@.target;
                     disabled; vendor preset: enabled)
             Active: inactive (dead)
        <BLANKLINE>
        ... systemd[...]: Reached target instance 1: dummy target.
        ... systemd[...]: Stopped target instance 1: dummy target.
        <BLANKLINE>
        >>> print(stderr)  # doctest:+NORMALIZE_WHITESPACE
        >>> my_unit.remove()
        """
        return await self._unit_cmd('start', instance=instance, env=env)

    async def stop(self,
                   instance: typing.Optional[str] = None,
                   env: typing.Optional[dict] = None):
        return await self._unit_cmd('stop', instance=instance, env=env)

    async def enable(self,
                     instance: typing.Optional[str] = None,
                     env: typing.Optional[dict] = None):
        return await self._unit_cmd('enable', instance=instance, env=env)

    async def disable(self,
                      instance: typing.Optional[str] = None,
                      env: typing.Optional[dict] = None):
        return await self._unit_cmd('disable', instance=instance, env=env)

    async def daemon_reload(self):
        """Reload the systemd daemon

        Example:
        --------
        >>> import asyncio
        >>> out, err = asyncio.run(_Run(None).daemon_reload())
        """
        return await self.async_systemctl(
                unit='', command='daemon-reload')
