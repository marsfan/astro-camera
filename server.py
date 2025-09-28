#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Web server for hosting the astro camera remote control."""

# This is adapted from the nicegui_webcam sample to understand the camera
# logic
import signal
import time
from types import FrameType

import fastapi
import nicegui

DUMMY_CAMERA = True

if DUMMY_CAMERA:
    from camera_dummy import Camera
else:
    try:
        from camera_picam import Camera
    except ImportError:
        from camera_cv import Camera


class Server:
    """Main web interface for camera control."""

    def __init__(self) -> None:
        """Initialize server."""
        self._camera = Camera()

        # Sadly, FastAPI does not seem to work on class methods, so we
        # have to embed this function inside the setup function.

        @nicegui.app.get("/video/frame")
        async def grab_frame() -> fastapi.Response:
            """Grab a single frame from the camera and put it on the UI."""
            # Function with high IO and CPU wait times, so run in separate thread to avoid blocking
            # event loop
            # TODO: get_frame is also cpubound, so maybe we want to use cpu_bound instead?
            frame = await nicegui.run.io_bound(self._camera.get_frame)
            # frame = b"00"
            return fastapi.Response(content=frame, media_type="image/jpeg")

        # For non-flickering image updates and automatic bandwidth adaptation an interactive image is much better than `ui.image()`.
        video_image = nicegui.ui.interactive_image()  # .classes("w-full h-full")

        # Timer to constantly update image source
        # We are appending current timestamp to the source to force browser caching to update
        nicegui.ui.timer(
            interval=0.1,
            callback=lambda: video_image.set_source(
                f"/video/frame?{time.time()}")
        )

        # Defining the main UI.
        # nicegui.ui.button("Take Photo", lambda: print(e))
        nicegui.ui.button("Take Photo", on_click=self._camera.take_photo)
        nicegui.ui.label("Exposure Control").style(
            "font-size: 20px; font-weight: bold"
        )
        ae_switch = nicegui.ui.switch("Auto Exposure")
        nicegui.ui.number(label="Exposure").bind_enabled_from(
            ae_switch,
            "value",
            # Inverts the switch value, so when switch is on, we disable widget
            backward=lambda value: not value
        )
        nicegui.ui.number(label="Gain").bind_enabled_from(ae_switch).bind_enabled_from(
            ae_switch,
            "value",
            # Inverts the switch value, so when switch is on, we disable widget
            backward=lambda value: not value
        )
        with nicegui.ui.row().classes('w-full no-wrap'):
            slider = nicegui.ui.slider(
                min=-8,
                max=8,
                step=0.1,
                value=0
            ).style("max-width: 180px").bind_enabled_from(
                ae_switch,
                "value",
                # Inverts the switch value, so when switch is on, we disable widget
                backward=lambda value: not value
            )
            nicegui.ui.label().bind_text_from(slider, "value")
            nicegui.ui.label("EV")

        with nicegui.ui.row():
            nicegui.ui.button("Set Options")
            nicegui.ui.button("Reset Options")
        nicegui.ui.button("Dump Stuff")

        nicegui.app.on_shutdown(self.cleanup)
        # We also need to disconnect clients when the app is stopped with Ctrl+C,
        # because otherwise they will keep requesting images which lead to unfinished subprocesses blocking the shutdown.
        signal.signal(signal.SIGINT, self.handle_sigint)

    async def cleanup(self) -> None:
        """Cleanup the user interface."""
        # This prevents ugly stack traces when auto-reloading on code change,
        # because otherwise disconnected clients try to reconnect to the newly started server.
        await self.disconnect()
        # Release the webcam hardware so it can be used by other applications again.
        self._camera.close()

    async def disconnect(self) -> None:
        """Disconnect all clients from the running server."""
        for client_id in nicegui.Client.instances:
            await nicegui.core.sio.disconnect(client_id)

    def handle_sigint(self, sig_num: int, frame: FrameType | None) -> None:
        """Handle getting sigint to quit server."""
        # Since disconnect is async, we have to call it from event loop
        nicegui.ui.timer(0.1, self.disconnect, once=True)

        # Delay handler to allow disconnect to complete
        nicegui.ui.timer(
            1,
            lambda: signal.default_int_handler(sig_num, frame),
            once=True
        )


if __name__ in {"__main__", "__mp_main__"}:
    # nicegui.app.on_startup(setup)
    Server()
    nicegui.ui.run()
