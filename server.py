#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Web server for hosting the astro camera remote control."""

# This is adapted from the nicegui_webcam sample to understand the camera
# logic
import json
import signal
import time
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import Any

import fastapi
import nicegui

DUMMY_CAMERA = True

if DUMMY_CAMERA:
    from astro_camera.camera.dummy import Camera
else:
    try:
        from astro_camera.camera.picam import Camera
    except ImportError:
        from astro_camera.camera.webcam import Camera


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

        nicegui.ui.page_title("Astro Camera Control")

        # For non-flickering image updates and automatic bandwidth
        # adaptation an interactive image is much better than `ui.image()`.
        video_image = nicegui.ui.interactive_image()  # .classes("w-full h-full")

        self.ev = 0.0
        self.exposure = 0.0125  # 1/8 second
        self.gain = 1.0
        self.ae_enable = True

        # Timer to constantly update image source
        # We are appending current timestamp to the source to force browser caching to update
        nicegui.ui.timer(
            interval=0.1,
            callback=lambda: video_image.set_source(
                f"/video/frame?{time.time()}")
        )

        # Defining the main UI.
        # nicegui.ui.button("Take Photo", lambda: print(e))
        nicegui.ui.button("Take Photo", on_click=self.take_photo)
        nicegui.ui.label("Exposure Control").style(
            "font-size: 20px; font-weight: bold"
        )
        self.ae_switch = nicegui.ui.switch(
            "Auto Exposure").bind_value(self, "ae_enable")
        self.exposure_entry = nicegui.ui.number(label="Exposure").bind_enabled_from(
            self.ae_switch,
            "value",
            # Inverts the switch value, so when switch is on, we disable widget
            backward=lambda value: not value
        ).bind_value(self, "exposure")
        self.gain_entry = nicegui.ui.number(label="Gain").bind_enabled_from(
            self.ae_switch,
            "value",
            # Inverts the switch value, so when switch is on, we disable widget
            backward=lambda value: not value
        ).bind_value(self, "gain")
        with nicegui.ui.row().classes('w-full no-wrap'):
            self.ev_slider = nicegui.ui.slider(
                min=-8,
                max=8,
                step=0.1,
                value=0
            ).style("max-width: 180px").bind_value(self, "ev")
            nicegui.ui.label().bind_text_from(self, "ev")
            nicegui.ui.label("EV")

        with nicegui.ui.row():
            nicegui.ui.button(
                "Set Options",
                on_click=self.set_camera_props
            )
            nicegui.ui.button(
                "Reset Options",
                on_click=self.reset_camera_props
            )
        nicegui.ui.button(
            "Dump Stuff",
            on_click=self.debug
        )

        nicegui.app.on_shutdown(self.cleanup)
        # We also need to disconnect clients when the app is stopped with Ctrl+C,
        # because otherwise they will keep requesting images which lead to
        # unfinished subprocesses blocking the shutdown.
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

    async def take_photo(self) -> None:
        """Take a photo with the camera, and save the photo on disk."""
        camera_data, jpg_photo, dng_photo = self._camera.take_photo()

        filename = f"IMG_{datetime.isoformat(datetime.now())}".replace(":", "_")  # noqa
        Path(f"{filename}.jpg").write_bytes(jpg_photo)
        Path(f"{filename}.dng").write_bytes(dng_photo)
        with Path(f"{filename}_metadata.json").open("w", encoding="UTF-8") as file:
            json.dump(camera_data, file, indent=4)

    async def set_camera_props(self) -> None:
        """Set the camera configuration properties."""
        modified_controls: dict[str, Any] = {}

        if not self.ae_switch.value:

            modified_controls["ExposureTime"] = self.exposure_entry.value
            modified_controls["AnalogueGain"] = self.gain_entry.value
            modified_controls["ExposureValue"] = self.ev
            modified_controls["AeEnable"] = False
        else:
            modified_controls["ExposureValue"] = self.ev
            modified_controls["AeEnable"] = True

        self._camera.set_controls(modified_controls)

    async def reset_camera_props(self) -> None:
        """Reset camera configuration properties."""
        self.ev = 0
        self.ae_enable = True
        self._camera.set_controls(
            {
                "AeEnable": self.ae_enable,
                "ExposureValue": self.ev
            }
        )

    async def debug(self) -> None:
        """Print camera information to console."""
        print(self._camera.get_controls())
        print(self._camera.get_metadata())


if __name__ in {"__main__", "__mp_main__"}:
    Server()
    nicegui.ui.run()
