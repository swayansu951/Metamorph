import asyncio
import sys

import uvicorn


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
