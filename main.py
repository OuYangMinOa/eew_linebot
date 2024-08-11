import asyncio


from src.config        import PORT
from src.app           import app

from hypercorn.asyncio import serve
from hypercorn.config  import Config

from src.eew_loop      import EEWLoop

async def START_SERVICES():
    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    config.debug = False
    await serve(app, config)

    # app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    # # Start the ngrok service
    import ngrok
    listener = ngrok.forward(PORT,authtoken_from_env=True)
    print(f"[*] Url : {listener.url()}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # # Start the earthquake early warning service in a thread
    EEWLoop(loop)\
        .start_alert_tw()\
        .start_alert_jp()\
        .start_alert_sc()\
        .start_alert_fj()\
        

    # Start the web server
    loop.run_until_complete(START_SERVICES())
