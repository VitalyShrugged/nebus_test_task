import asyncio
import inspect
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Callable


_background_tasks: set[asyncio.Task] = set()


async def handler_executor(functions: list[Callable]) -> None:
    if not functions:
        return None
    loop = asyncio.get_running_loop()

    sync_functions = [func for func in functions if not inspect.iscoroutinefunction(func)]
    async_functions = [func for func in functions if inspect.iscoroutinefunction(func)]

    if sync_functions:
        executor = ThreadPoolExecutor(max_workers=len(sync_functions))
        for func in sync_functions:
            loop.run_in_executor(executor, func)

    for func in async_functions:
        task = loop.create_task(func())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    await asyncio.sleep(1)
    return None
