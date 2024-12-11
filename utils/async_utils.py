import asyncio
from concurrent.futures import ThreadPoolExecutor
from config import MAX_CONCURRENT_TASKS

executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS)

processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

async def run_in_executor(func, *args):
    async with processing_semaphore:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, func, *args)

async def shutdown_executor():
    executor.shutdown(wait=True)
