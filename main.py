import ngrok
import asyncio


from src.config        import PORT
from src.app           import app

from hypercorn.asyncio import serve
from hypercorn.config  import Config

from src.eew_loop      import start_eew_loop

async def START_SERVICES():
    config = Config()
    config.bind = [f"127.0.0.1:{PORT}"]
    config.debug = False
    await serve(app, config)

    # app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    # # Start the ngrok service
    listener = ngrok.forward(PORT,authtoken_from_env=True)
    print(f"[*] Url : {listener.url()}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # # Start the eew service in a thread
    start_eew_loop(loop)

    # Start the web server
    loop.run_until_complete(START_SERVICES())

