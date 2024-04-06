import asyncio


from src.app           import app
from src.config        import PORT
from hypercorn.asyncio import serve
from hypercorn.config  import Config
from src.eew_loop      import start_eew_loop


async def START_SERVICES():
    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    config.debug = False
    await serve(app, config)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    start_eew_loop(loop)
    loop.run_until_complete(START_SERVICES())

