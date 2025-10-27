#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Web server for hosting the astro camera remote control."""

# This is adapted from the nicegui_webcam sample to understand the camera
# logic
import asyncio
import json
import logging
import signal
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any

import fastapi
import nicegui

from .camera import CameraBase

# FIXME: Seems that if we leave AE on, we can set just exposure or gain
# and the other will auto set. Do we want to enable this?
# FIXME: Support dynamic setting of min/max values for inputs from configuration


def create_nav_elements() -> None:
    """Create navigation  elements for all pages."""
    left_drawer = nicegui.ui.left_drawer(
        value=False,
        fixed=False,
    )
    left_drawer.classes("items-left")
    left_drawer.props("width=100")

    with nicegui.ui.header(elevated=True):
        nicegui.ui.button(
            on_click=left_drawer.toggle,
            icon="menu",
        )
    with left_drawer:
        nicegui.ui.menu_item(
            "Home",
            on_click=lambda: nicegui.ui.navigate.to("/"),
        )


def update_gain_exposure_disable(owner: "Server", _value: bool) -> None:
    """Update the variable that is used to disable gain and exposure entry.

    This is necessary as there are multiple properties that the enabled
    state of the exposure and gain properties depend on.

    Arguments:
        owner: The object that the variable is owned by
        _value: The newly set value. Not used

    """
    owner.exposure_gain_state = not (
        owner.capture_in_progress or owner.ae_enable)


class Server:
    """Main web interface for camera control."""

    capture_in_progress = nicegui.binding.BindableProperty(
        update_gain_exposure_disable,
    )

    ae_enable = nicegui.binding.BindableProperty(
        update_gain_exposure_disable,
    )

    def count_up(self) -> None:
        """Increment the counter, rolling over at 100."""
        self.counter += 1
        self.counter %= 100

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

        self.counter = 0

        self.exposure_gain_state = False

        self.capture_in_progress = False

        nicegui.app.on_shutdown(self.cleanup)
        # We also need to disconnect clients when the app is stopped with
        # Ctrl+C, because otherwise they will keep requesting images which lead
        # to unfinished subprocesses blocking the shutdown.
        signal.signal(signal.SIGINT, self.handle_sigint)

        # Sadly, FastAPI does not seem to work on class methods, so
        # we have to embed decorated functions inside this one
        # in order to allow access to class members

        nicegui.app.timer(0.1, callback=self.count_up)

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
            create_nav_elements()
            # For non-flickering image updates and automatic bandwidth
            # adaptation an interactive image is much better than `ui.image()`.

            video_image = nicegui.ui.interactive_image()
            video_image.style("max-width: 960px")
            with video_image:
                spinner = nicegui.ui.spinner(size="10em")
                spinner.visible = False
                spinner.bind_visibility_from(self, "capture_in_progress")
                spinner.classes(
                    "absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
                )

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

            # TODO: Remove this and replace with a nicer visualization?
            # This is a counter that I'm using as a visual indicator for
            # when the WebUI lags.
            # nicegui.ui.label().bind_text_from(self, "counter")
            nicegui.ui.button("Take Photo", on_click=self.take_photo).bind_enabled_from(
                self,
                "capture_in_progress", backward=lambda v: not v,
            )

            nicegui.ui.label("Exposure Control").style(
                "font-size: 20px; font-weight: bold",
            )

            ae_switch = nicegui.ui.switch("Auto Exposure")
            ae_switch.bind_value(self, "ae_enable")
            ae_switch.on_value_change(
                lambda v: self._camera.set_auto_exposure(v.value),
            )
            ae_switch.bind_enabled_from(
                self,
                "capture_in_progress", backward=lambda v: not v,
            )

            with nicegui.ui.row():
                exposure_entry = nicegui.ui.number(label="Exposure")
                exposure_entry.bind_value(self, "exposure")
                exposure_entry.bind_enabled_from(
                    self,
                    "exposure_gain_state",
                )

                nicegui.ui.label().bind_text_from(
                    self,
                    "current_exposure",
                    backward=lambda v: f"Current Exposure Time: {v:0.1f}",
                )
            with nicegui.ui.row():
                gain_entry = nicegui.ui.number(label="Gain")
                gain_entry.bind_value(self, "gain")
                gain_entry.bind_enabled_from(self, "exposure_gain_state")
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
                ).style("max-width: 180px").bind_value(self, "ev").on_value_change(
                    lambda v: self._camera.set_ev(v.value),
                ).bind_enabled_from(
                    self,
                    "capture_in_progress",
                    lambda v: not v,
                )
                nicegui.ui.label().bind_text_from(self, "ev")
                nicegui.ui.label("EV")

            with nicegui.ui.row():
                nicegui.ui.button(
                    "Set Options",
                    on_click=self.set_camera_props,
                ).bind_enabled_from(
                    self,
                    "capture_in_progress",
                    lambda v: not v,
                )
                nicegui.ui.button(
                    "Reset Options",
                    on_click=self.reset_camera_props,
                ).bind_enabled_from(
                    self,
                    "capture_in_progress",
                    lambda v: not v,
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
        # FIXME: Taking the photo and encoding to DNG is CPU bound, but we
        # can't pickle the camera class
        # due to unpickeable libcamera stuff. Need to figure this out
        # Either maybe we should push all camera to separate thread and use a
        # loopback or leverage some of the async stuff built into the module
        # github.com/raspberrypi/picamera2/issues/714
        self.capture_in_progress = True
        camera_data, jpg_photo, dng_photo = await self._camera.take_photo_async()
        await nicegui.run.io_bound(
            self.write_photos,
            jpg_photo,
            dng_photo,
            camera_data,
        )
        self.capture_in_progress = False

    # Making this static so that we can await it without needing to pickle full
    # class if changed to use cpu_bound
    # See https://github.com/zauberzeug/nicegui/discussions/2221#discussioncomment-7920864
    @staticmethod
    def write_photos(
        jpg_bytes: bytes,
        dng_bytes: bytes,
        metadata: dict[str, Any],
    ) -> None:
        """Save the taken image.

        Arguments:
            jpg_bytes: The bytes to save for the JPG photo.
            dng_bytes: The bytes to save as a DNG file
            metadata: Dictionary of the metadata to save to a JSON.

        """
        filename = f"IMG_{datetime.isoformat(datetime.now(UTC))}".replace(":", "_")  # noqa: E501
        Path(f"{filename}.jpg").write_bytes(jpg_bytes)
        Path(f"{filename}.dng").write_bytes(dng_bytes)
        Path(f"{filename}.metadata.json").write_text(
            json.dumps(metadata, indent=4),
            "UTF-8",
        )

    async def set_camera_props(self) -> None:
        """Set the camera configuration properties."""
        modified_controls: dict[str, Any] = {}

        if not self.ae_enable:
            modified_controls["ExposureTime"] = int(self.exposure * 1000000)
            modified_controls["AnalogueGain"] = self.gain

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

    async def update_image(
        self,
        video_image: nicegui.ui.interactive_image,
    ) -> None:
        """Update the data from the camera on the web UI.

        Arguments:
            video_image: Image to update

        """
        video_image.set_source(f"/video/frame?{time.time()}")
        metadata = await self._camera.get_metadata_async()
        self.current_exposure = metadata["ExposureTime"]
        self.current_gain = metadata["AnalogueGain"]
        # FIXME: Not in metadata, where do I get this?
        # self.current_ev = metadata["ExposureValue"]  # noqa: ERA001


def setup_debug() -> None:
    """Enable various parameters to help debug asyncio."""
    loop = asyncio.get_running_loop()

    # Print out to console any time a task takes more than 0.05 seconds
    # to execute
    loop.set_debug(True)
    loop.slow_callback_duration = 0.05

    # Set all non-picamera2 logs to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("picamera2").setLevel(logging.WARNING)

    # Don't suppress some warnings that might be useful to catch
    warnings.filterwarnings("always", category=ResourceWarning)
    warnings.filterwarnings("always", category=RuntimeWarning)


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
    if debug:
        nicegui.app.on_startup(setup_debug)
    Server(camera)
    nicegui.ui.run(reload=debug, show=False, dark=True)
