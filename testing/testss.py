import asyncio
import time

def blocking_io():
    """A synchronous, blocking function."""
    print(f"start blocking_io at {time.strftime('%X')}")
    # This sleep represents any blocking IO-bound operation.
    time.sleep(2)
    print(f"blocking_io complete at {time.strftime('%X')}")

async def main():
    print(f"started main at {time.strftime('%X')}")

    # 1. Create a coroutine object for the blocking call
    coro = asyncio.to_thread(blocking_io)
    
    # 2. Schedule it to run as a background task
    #    This returns a Task object immediately, and the code continues.
    task = asyncio.create_task(coro)

    # The main function no longer awaits here, so it prints the next line instantly.
    print(f"finished main at {time.strftime('%X')}")
    
    # 3. (Important!) Wait for the background task to finish before the
    #    program exits. Otherwise, the script might end before blocking_io completes.
    await task

# To run the async main function
if __name__ == "__main__":
    asyncio.run(main())