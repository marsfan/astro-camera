#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Module for manipulating camera via PiCamera2."""

import asyncio
from collections.abc import Buffer
from copy import deepcopy
from io import BufferedIOBase, BytesIO
from threading import Condition
from typing import Any

from picamera2.encoders import MJPEGEncoder  # type: ignore[attr-defined]
from picamera2.job import Job
from picamera2.outputs.fileoutput import FileOutput
from picamera2.picamera2 import Picamera2
from picamera2.request import CompletedRequest

from . import CameraBase


def _photo_signal(
    job: Job,
    loop: asyncio.AbstractEventLoop,
    future: asyncio.Future,
) -> None:
    """Signal function to set a future to indicate that taking a photo is done.

    Arguments:
        job: The picamera2 job for the photo taken.
        loop: The asyncio event loop that the future to set is in.
        future: The future to set the result for.

    """
    loop.call_soon_threadsafe(future.set_result, "Done")


class StreamingOutput(BufferedIOBase):
    """Simulated Buffered IO to write the frames to as they are encoded."""

    def __init__(self) -> None:
        """Initialize the writer."""
        self.frame: bytes | None = None
        self.condition = Condition()

    def write(self, buf: Buffer) -> int:
        """Write the bytes to the frame.

        Arguments:
            buf: The buffer to write

        Returns:
            Number of written bytes

        """
        with self.condition:
            self.frame = BytesIO(buf).read()
            self.condition.notify_all()
            return len(self.frame)


class PiCamera(CameraBase):
    """Class for manipulating camera via PiCamera2."""

    def __init__(self) -> None:
        """Initialize Camera."""
        # FIXME: Support initialization args for controls.
        # and preview config (namely size)
        self._cam_controls: dict[str, Any] = {
            "AeEnable": True,
            "ExposureValue": 0.0,
        }
        self._preview_config: dict[str, Any] = {}
        self._picam2: Picamera2 | None = None

        self._output = StreamingOutput()

    def initialize_hw(self) -> None:
        """Initialize the camera hardware."""
        self._picam2 = Picamera2()
        self._preview_config = self._picam2.create_video_configuration(
            main={"size": (640, 480)},
            controls=self._cam_controls,
        )
        self._picam2.configure(self._preview_config)
        self._picam2.start_recording(MJPEGEncoder(), FileOutput(self._output))

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        Raises:
            ValueError: Raised if the frame was none on return.

        """
        # TODO: Ensure we are using hw encoder
        # https://github.com/raspberrypi/picamera2/issues/752
        # FIXME: Might need to figure out how to make this async as well
        with self._output.condition:
            self._output.condition.wait()
            if self._output.frame is None:
                raise ValueError("Frame was None")
            return self._output.frame

    def _prepare_to_take(self) -> dict[str, Any]:
        """Prepare to take a high resolution photo.

        This will stop the preview encoder and create a still
        configuration for the capture.

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")
        # Create config for high res photo
        capture_config = self._picam2.create_still_configuration(
            raw={},
            display=None,
            controls=self._cam_controls,
        )
        # Stop the encoder to prevent crashes
        # See https://forums.raspberrypi.com/viewtopic.php?t=354226
        self._picam2.stop_encoder()

        return capture_config

    def _process_request_and_release(
        self,
        request: CompletedRequest,
    ) -> tuple[dict[str, Any], bytes, bytes]:
        """Process the request into the output images, and release it, and restart encoder.

        Arguments:
            request: The request to process

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")
        # Create buffers to hold the encoded images
        dng_buf = BytesIO()
        jpg_buf = BytesIO()

        # Save the images to the buffers
        # TODO: Encode bytes.
        # FIXME: Is there a way to do this without using a BytesIO?
        request.save("main", jpg_buf, format="jpg")
        request.save_dng(dng_buf)

        # Built metadata structure
        data = {
            "cam_driver": "picamera2",
            "metadata": request.get_metadata(),
            # "config": request.config, # FIXME: Get this working # noqa: ERA001,E501
            "camera_properties": self._picam2.camera_properties,
        }

        # Restart the encoder
        # FIXME: Logic to check if its already started?
        self._picam2.start_encoder(MJPEGEncoder(), FileOutput(self._output))

        # Release the request
        request.release()

        return data, jpg_buf.getvalue(), dng_buf.getvalue()

    def take_photo(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")

        capture_config = self._prepare_to_take()

        # Take the photo
        # FIXME: After it switches back, controls are defaults, not last
        # user specified values
        # FIXME: Function docstring say to try using switch_mode_capture_request_and_stop instead
        request = self._picam2.switch_mode_and_capture_request(
            capture_config,
        )

        return self._process_request_and_release(request)

    async def take_photo_async(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a high-resolution photo asynchronously.

        This is the same as :py:meth:`take_photo`, but it takes the photo
        in an asynchronous manner, so that the function can be awaited
        until the camera is done capturing. This allows us to prevent
        blocking other operations in a async event loop.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")
        capture_config = self._prepare_to_take()
        # Take the photo
        # FIXME: After it switches back, controls are defaults, not last
        # user specified values
        # FIXME: Function docstring say to try using switch_mode_capture_request_and_stop instead
        loop = asyncio.get_running_loop()
        photo_done = asyncio.get_running_loop().create_future()

        job = self._picam2.switch_mode_and_capture_request(
            capture_config,
            signal_function=lambda j: _photo_signal(j, loop, photo_done),
        )

        # Wait for the capture to complete, releasing the async loop
        await photo_done

        return self._process_request_and_release(job.get_result())

    def get_metadata(self) -> dict[str, float]:
        """Get camera metadata.

        Returns:
            Camera metadata.

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")
        return self._picam2.capture_metadata()

    async def get_metadata_async(self) -> dict[str, float]:
        """Get camera metadata with async support.

        Returns:
            Camera metadata.

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")
        loop = asyncio.get_running_loop()
        done = loop.create_future()
        job = self._picam2.capture_metadata(
            wait=False,
            signal_function=lambda j: _photo_signal(j, loop, done),
        )
        await done
        return job.get_result()

    def get_controls(self) -> dict[str, Any]:
        """Get camera controls.

        Returns:
            Camera Controls

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")
        return self._picam2.camera_controls

    def set_controls(self, controls: dict[str, Any]) -> None:
        """Set camera controls.

        Arguments:
            controls: The camera controls to set.

        """
        if not self._picam2:
            raise ValueError("Camera is not initialized.")
        self._cam_controls = controls

        # We need to change controls to allow for frame to take
        # longer than default. If we don't change this, controls will
        # be locked at lower value than we specified.
        # https://forums.raspberrypi.com/viewtopic.php?t=291474
        if "ExposureTime" in self._cam_controls:
            self._cam_controls["FrameDurationLimits"] = (
                0,
                controls["ExposureTime"] + 1000,
            )
        else:
            self._cam_controls["FrameDurationLimits"] = (
                0,
                1000000,
            )

        # Setting preview controls, we want to clamp exposure time to
        # no more than 1/5 sec to maintain a useable framerate
        # FIXME: Need a way to indicate this on the UI.
        # UI probably needs a "current values" readout.
        preview_controls = deepcopy(controls)
        if "ExposureTime" in controls:
            preview_controls["ExposureTime"] = min(
                controls["ExposureTime"],
                200000,
            )
            preview_controls["FrameDurationLimits"] = (
                0,
                controls["ExposureTime"] + 1000,
            )

        self._picam2.set_controls(preview_controls)

    def set_exposure_time(self, time: float) -> None:
        """Set the exposure time.

        Arguments:
            time: The exposure time to set

        """
        self._cam_controls["ExposureTime"] = time

    def set_gain(self, gain: float) -> None:
        """Set sensor gain.

        Arguments:
            gain: The sensor gain to set.

        """
        self._cam_controls["AnalogueGain"] = gain

    def set_ev(self, ev: float) -> None:
        """Set sensor exposure compensation.

        Arguments:
            ev: The exposure compensation to set.

        """
        self._cam_controls["ExposureValue"] = ev

    def set_auto_exposure(self, ae: bool) -> None:
        """Enable/Disable auto-exposure.

        Arguments:
            ae: Whether or not to enable auto-exposure

        """
        self._cam_controls["AeEnable"] = ae

    def get_exposure_time(self) -> float:
        """Get the exposure time.

        Returns:
            Exposure Time

        """
        return self.get_metadata()["ExposureTime"]

    def get_gain(self) -> float:
        """Get sensor gain.

        Returns:
            Sensor Gain

        """
        return self.get_metadata()["AnalogueGain"]

    def get_ev(self) -> float:
        """Get sensor exposure compensation.

        Returns:
            Exposure Compensation

        """
        assert isinstance(self._cam_controls["ExposureValue"], float)
        return self._cam_controls["ExposureValue"]

    def get_auto_exposure(self) -> bool:
        """Get whether or not auto-exposure is enabled.

        Returns:
            Whether or not auto-exposure is enabled

        """
        assert isinstance(self._cam_controls["AeEnable"], bool)
        return self._cam_controls["AeEnable"]

    def close(self) -> None:
        """Shut down camera."""
        if self._picam2:
            self._picam2.stop_recording()
            self._picam2.close()
