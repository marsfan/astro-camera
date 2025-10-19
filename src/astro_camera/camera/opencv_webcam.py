#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Module for manipulating camera via OpenCV."""
import time
from threading import Condition, Event, Thread
from typing import TYPE_CHECKING, Any

import cv2

if TYPE_CHECKING:
    from cv2.typing import MatLike

from . import CameraBase

# TODO: Context manager suppot
# TODO: Metdata suport, exposure support
# FIXME: Frame rate for this is really awful. Need to look into it more.


class CameraThread(Thread):
    """Thread for reading from the camera."""

    def __init__(self, camera_index: int) -> None:
        """Initialize the camera, and the thread.

        Thread is not yet started. We have just initialized things.
        call :py:meth:`start` to start the thread.

        """
        super().__init__(name="CV2 Webcamera")
        self._camera_index = camera_index
        self._capture: cv2.VideoCapture | None = None
        self.image_condition = Condition()
        self._running = Event()
        self.full_photo: None | MatLike = None
        self.frame: None | MatLike = None

    def run(self) -> None:
        """Main logic for the thread.

        This should not be called directly. Instead :py:meth:`start`
        should be called.

        """
        self._capture = cv2.VideoCapture(self._camera_index)

        # FIXME: Need to have logic to clear the event so we shutdown cleanly
        self._running.set()
        while self._running.is_set():
            rc, img = self._capture.read()
            if not rc:
                raise RuntimeError("Failed to read frame.")
            rc, full_jpg = cv2.imencode(".jpg", img)
            if not rc:
                raise RuntimeError("Failed to encode full image.")
            height, width, _ = img.shape
            scaled = cv2.resize(
                img,
                (640, int(640 / width * height)),
            )
            rc, scaled_jpg = cv2.imencode(".jpg", scaled)
            if not rc:
                raise RuntimeError("Failed to encode preview image")
            with self.image_condition:
                self.full_photo = full_jpg
                self.frame = scaled_jpg
                self.image_condition.notify_all()

            # We don't want to run too fast, or the thread will take
            # up too many resources.
            # So we sleep enough to get (in theory) 30FPS
            time.sleep(1/30)

        # Close camera
        self._capture.release()

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        Raise:
            TypeError: Raised if the photo was none when trying to
                return it.

        """
        with self.image_condition:
            self.image_condition.wait()
            if self.frame is None:
                raise TypeError("Frame was none")
            return bytes(self.frame)

    def get_photo(self) -> bytes:
        """Get the full sized image.

        Returns:
            Bytes for the JPEG of the full sized image.

        Raise:
            TypeError: Raised if the photo was none when trying to
                return it.

        """
        with self.image_condition:
            self.image_condition.wait()
            if self.full_photo is None:
                raise TypeError("Frame was None")
            return bytes(self.full_photo)


class OpenCVWebcam(CameraBase):
    """Class for manipulating camera via OpenCV."""

    def __init__(self) -> None:
        """Initialize camera."""
        self._capture: cv2.VideoCapture | None = None
        # FIXME: Need a way to select the correct index.
        # On laptop, built in webcam tends to be index 0,
        self._camera_thread = CameraThread(0)

    def initialize_hw(self) -> None:
        """Initialize the camera hardware."""
        self._camera_thread.start()

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
        return self._camera_thread.get_frame()

    def take_photo(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        data: dict[str, Any] = {
            "cam_driver": "cv2",
            "metadata": self.get_metadata(),
            # "config": request.config, # FIXME: Get this working # noqa: ERA001,E501

            # FIXME: DO this with OpenCV
            "camera_properties": {},
            # "camera_properties": self._picam2.camera_properties
        }

        # FIXME: Need to figure out how to encode DNG. Seems OpenCV
        # Does not have that by default.
        return data, self._camera_thread.get_photo(), b""

    async def take_photo_async(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        # FIXME: Figure out how to actually make this async
        if self._capture is None:
            raise ValueError("Camera HW has not been initialized.")
        # FIXME: Need to figure out how to encode DNG. Seems OpenCV
        # Does not have that by default.
        rc, img = self._capture.read()
        if not rc:
            raise RuntimeError("Failed to read frame.")

        rc, jpg = cv2.imencode(".jpg", img)
        if not rc:
            raise RuntimeError("Failed to encode frame.")
        # FIXME: Include image metadata.

        data: dict[str, Any] = {
            "cam_driver": "cv2",
            "metadata": self.get_metadata(),
            # "config": request.config, # FIXME: Get this working # noqa: ERA001,E501

            # FIXME: DO this with OpenCV
            "camera_properties": {},
            # "camera_properties": self._picam2.camera_properties
        }

        return data, bytes(jpg), b""

    def get_metadata(self) -> dict[str, float]:
        """Get camera metadata.

        Returns:
            Camera Metadata.

        """
        # FIXME: Figure out how to do this in OpenCV
        return {
            "ExposureTime": 0,
            "AnalogueGain": 0,
        }

    async def get_metadata_async(self) -> dict[str, float]:
        """Get camera metadata.

        Returns:
            Camera Metadata.

        """
        # FIXME: Figure out how to do this in OpenCV
        return {
            "ExposureTime": 0,
            "AnalogueGain": 0,
        }

    def get_controls(self) -> dict[str, float]:
        """Get camera controls.

        Returns:
            Camera Controls

        """
        # FIXME: Figure out for OpenCV
        return {"AeEnable": False, "ExposureValue": 0.0}

    def set_controls(self, controls: dict[str, bool | float]) -> None:
        """Set camera controls.

        Arguments:
            controls: The camera controls to set.

        """
        # TODO: Figure out how to do this for OpenCV

    def set_exposure_time(self, time: float) -> None:
        """Set the exposure time.

        Arguments:
            time: The exposure time to set

        """

    def set_gain(self, gain: float) -> None:
        """Set sensor gain.

        Arguments:
            gain: The sensor gain to set.

        """

    def set_ev(self, ev: float) -> None:
        """Set sensor exposure compensation.

        Arguments:
            ev: The exposure compensation to set.

        """

    def set_auto_exposure(self, ae: bool) -> None:
        """Enable/Disable auto-exposure.

        # Arguments:
        #     ae: Whether or not to enable auto-exposure

        """
        raise ValueError("ABC")

    def get_exposure_time(self) -> float:
        """Get the exposure time.

        Returns:
            Exposure Time

        """
        # FIXME: Actually read this
        return 0.0

    def get_gain(self) -> float:
        """Get sensor gain.

        Returns:
            Sensor Gain

        """
        # FIXME: Actually read this
        return 0.0

    def get_ev(self) -> float:
        """Get sensor exposure compensation.

        Returns:
            Exposure Compensation

        """
        # FIXME: Actually read this
        return 0.0

    def get_auto_exposure(self) -> bool:
        """Get whether or not auto-exposure is enabled.

        Returns:
            Whether or not auto-exposure is enabled

        """
        # FIXME: Actually read this
        return True

    def close(self) -> None:
        """Shut down camera."""
        if self._capture is not None:
            self._capture.release()
