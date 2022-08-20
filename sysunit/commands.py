import os
import asyncio

async def async_systemctl(unit: str,
                          command: str,
                          manager: str='--user',
                          env: dict=dict()
                          ):
    """Run systemctl command asynchronously 

    Returns:

    stdout, stderr
    """
    proc = await asyncio.create_subprocess_exec(
        'systemctl', manager, command, unit.fullname
    )
    return await proc.communicate()
    
