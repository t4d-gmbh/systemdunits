# SystemdUnits

Small package for reading and writing systemd unit files.

## Installation

Fetch the latest version directly from the repository:

    pip install --upgrade git+https://github.com/tools4digits/systemdunits.git

## Usage Examples

### Creating systemd units

Create a new target unit template using the default manager (i.e. `--user`),
write it to `~/.config/systemd/user`, start an instance, show the status,
stop it again and clean up:

```python

import asyncio
from sysunit import SystemUnit
my_target = SystemUnit('test-example@.target')
# some dummy content
my_target.from_dict(dict(
    Unit=dict(Description='Target instance %i'),
    Install=dict(WantedBy='multi-user.target')
))
# write it to disk
my_target.write()
# reload the systmd daemon (this is an async operation)
asyncio.run(my_target.run.daemon_reload())
# start an instance of this unit
asyncio.run(my_target.run.start(instance='eg1'))
# get the status
out, err = asyncio.run(my_target.run.status(instance='eg1'))
print(out)
# ● test-example@eg1.target - Target instance eg1
#  Loaded: loaded (.../.config/systemd/user/test-example@.target; disabled;
#          vendor preset: enabled)
#  Active: active since ... ago
#  ... systemd[...]: Reached target Target instance eg1.

# stop the instance again
asyncio.run(my_target.run.stop(instance='eg1'))
# remove the unit file again
my_target.remove()
```

## Development
### Testing
Testing is done with `unittest`, including `doctest`.

To run tests simply go to the project root folder and run:

    python -m unittest

## Copyright

Copyright © 2022 T4D GmbH
