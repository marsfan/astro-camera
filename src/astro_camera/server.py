#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Web server for hosting the astro camera remote control."""

# This is adapted from the nicegui_webcam sample to understand the camera
# logic
import json
import signal
import time
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any

import fastapi
import nicegui

from .camera import CameraBase


class Server:
    """Main web interface for camera control."""

    def __init__(self, camera: CameraBase) -> None:
        """Initialize server."""
        self._camera = camera

        self.ev = 0.0
        self.exposure = 0.0125  # 1/8 second
        self.gain = 8.0
        self.ae_enable = True

        self.current_exposure = 0.0125
        self.current_gain = 0.0
        self.current_ev = 0.0

        nicegui.app.on_shutdown(self.cleanup)
        # We also need to disconnect clients when the app is stopped with
        # Ctrl+C, because otherwise they will keep requesting images which lead
        # to unfinished subprocesses blocking the shutdown.
        signal.signal(signal.SIGINT, self.handle_sigint)

        # Sadly, FastAPI does not seem to work on class methods, so
        # we have to embed decorated functions inside this one
        # in order to allow access to class members

        # FIXME: Despite using async/await, this can still lag the webui.
        # Need to fix
        @nicegui.app.get("/video/frame")
        async def grab_frame() -> fastapi.Response:
            """Grab a single frame from the camera and put it on the UI."""
            # Function with high IO and CPU wait times, so run in separate
            # thread to avoid blocking event loop
            # TODO: get_frame is also cpubound for some drivers, so maybe we
            # want to use cpu_bound instead?
            frame = await nicegui.run.io_bound(self._camera.get_frame)
            return fastapi.Response(content=frame, media_type="image/jpeg")

        @nicegui.ui.page("/", title="Astro Camera Control")
        def root_page() -> None:
            """Create top level (i.e. root) page."""
            # For non-flickering image updates and automatic bandwidth
            # adaptation an interactive image is much better than `ui.image()`.
            video_image = nicegui.ui.interactive_image()

            # Timer to constantly update image source
            # We are appending current timestamp to the source to force browser
            # caching to update
            # FIXME: Need to have this outside of a specific page, and we
            # then update a variable all clients read from. That might fix
            # occasional crashes
            nicegui.ui.timer(
                interval=0.1,
                callback=lambda: self.update_image(video_image),
            )

            # Defining the main UI.
            nicegui.ui.button("Take Photo", on_click=self.take_photo)
            nicegui.ui.label("Exposure Control").style(
                "font-size: 20px; font-weight: bold",
            )
            ae_switch = nicegui.ui.switch(
                "Auto Exposure").bind_value(self, "ae_enable")
            with nicegui.ui.row():
                nicegui.ui.number(label="Exposure").bind_enabled_from(
                    ae_switch,
                    "value",
                    # Inverts the switch value, so when switch is on,
                    # we disable widget
                    backward=lambda value: not value,
                ).bind_value(self, "exposure")
                nicegui.ui.label().bind_text_from(
                    self,
                    "current_exposure",
                    backward=lambda v: f"Current Exposure Time: {v:0.1f}",
                )
            with nicegui.ui.row():
                nicegui.ui.number(label="Gain").bind_enabled_from(
                    ae_switch,
                    "value",
                    # Inverts the switch value, so when switch is on,
                    # we disable widget
                    backward=lambda value: not value,
                ).bind_value(self, "gain")
                nicegui.ui.label().bind_text_from(
                    self,
                    "current_gain",
                    backward=lambda v: f"Current Gain: {v:.1f}",
                )
            with nicegui.ui.row().classes("w-full no-wrap"):
                nicegui.ui.slider(
                    min=-8,
                    max=8,
                    step=0.1,
                    value=0,
                ).style("max-width: 180px").bind_value(self, "ev")
                nicegui.ui.label().bind_text_from(self, "ev")
                nicegui.ui.label("EV")

            with nicegui.ui.row():
                nicegui.ui.button(
                    "Set Options",
                    on_click=self.set_camera_props,
                )
                nicegui.ui.button(
                    "Reset Options",
                    on_click=self.reset_camera_props,
                )
            nicegui.ui.button(
                "Dump Stuff",
                on_click=self.debug,
            )

    async def cleanup(self) -> None:
        """Cleanup the user interface."""
        # This prevents ugly stack traces when auto-reloading on code change,
        # because otherwise disconnected clients try to reconnect to the newly
        # started server.
        await self.disconnect()
        # Release the webcam hardware so it can be used by other
        # applications again.
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
            once=True,
        )

    async def take_photo(self) -> None:
        """Take a photo with the camera, and save the photo on disk."""
        camera_data, jpg_photo, dng_photo = self._camera.take_photo()

        filename = f"IMG_{datetime.isoformat(datetime.now(UTC))}".replace(":", "_")  # noqa: E501
        # TODO: Can we await all three (asyncio.gather maybe?)
        await nicegui.run.io_bound(
            lambda: Path(f"{filename}.jpg").write_bytes(jpg_photo),
        )
        await nicegui.run.io_bound(
            lambda: Path(f"{filename}.dng").write_bytes(dng_photo),
        )
        await nicegui.run.io_bound(
            lambda: Path(f"{filename}.metadata.json").write_text(
                json.dumps(camera_data, indent=4),
                "UTF-8",
            ),
        )

    async def set_camera_props(self) -> None:
        """Set the camera configuration properties."""
        modified_controls: dict[str, Any] = {}

        if not self.ae_enable:

            modified_controls["ExposureTime"] = int(self.exposure * 1000000)
            modified_controls["AnalogueGain"] = self.gain
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
                "ExposureValue": self.ev,
            },
        )

    async def debug(self) -> None:
        """Print camera information to console."""
        print("Camera Controls:")
        for key, value in self._camera.get_controls().items():
            print(f"\t{key}:\t{value}")
        print("Camera Metadata:")
        for key, value in self._camera.get_metadata().items():
            print(f"\t{key}:\t{value}")

    def update_image(
            self,
            video_image: nicegui.ui.interactive_image,
    ) -> None:
        """Update the data from the camera on the web UI.

        Arguments:
            video_image: Image to update

        """
        video_image.set_source(f"/video/frame?{time.time()}")
        metadata = self._camera.get_metadata()
        self.current_exposure = metadata["ExposureTime"]
        self.current_gain = metadata["AnalogueGain"]
        # FIXME: Not in metadata, where do I get this?
        # self.current_ev = metadata["ExposureValue"]


def server_main(camera: CameraBase, *, debug: bool = False) -> None:
    """Run the webui server.

    Warning:
        The ``debug`` parameter should not be used unless the
        function is directly called from a main guard.

    Arguments:
        camera: The camera to use with the webui.
        debug: Whether or not to enable auto-reload when package
            files are modified, and auto-open the webpage on launch.

    """
    nicegui.app.on_startup(camera.initialize_hw)
    Server(camera)
    nicegui.ui.run(reload=debug, show=False, dark=True)
