#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Module for manipulating camera via OpenCV."""
from typing import Any

import cv2

from . import CameraBase

# TODO: Context manager suppot
# TODO: Metdata suport, exposure support
# FIXME: Frame rate for this is really awful. Need to look into it more.


class OpenCVWebcam(CameraBase):
    """Class for manipulating camera via OpenCV."""

    def __init__(self) -> None:
        """Initialize camera."""
        self._capture: cv2.VideoCapture | None = None

    def initialize_hw(self) -> None:
        """Initialize the camera hardware."""
        # FIXME: Need a way to select the correct index.
        # On laptop, built in webcam tends to be index 0,
        # on RPI5, order seems to jump around.
        self._capture = cv2.VideoCapture(0)

        # Perform one capture to start up the webcam.
        self._capture.read()

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
        if self._capture is None:
            raise ValueError("Camera HW has not been initialized.")
        rc, img = self._capture.read()
        if not rc:
            raise RuntimeError("Failed to read frame.")

        # Internally, the image array is height X width.
        # But then the resize function expects us to provide width X height
        height, width, _ = img.shape
        img = cv2.resize(img, (640, int(640 / width * height)))
        rc, frame = cv2.imencode(".jpg", img)
        if not rc:
            raise RuntimeError("Failed to encode frame.")
        return bytes(frame)

    def take_photo(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
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
