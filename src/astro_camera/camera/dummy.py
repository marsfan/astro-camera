#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Dummy camera driver, using a video to simulate a camera."""


from time import monotonic
from typing import Any

import cv2

from . import CameraBase


class DummyCamera(CameraBase):
    """Base class for interacting with a camera."""

    def __init__(self) -> None:
        """Initialize camera."""
        self._video = cv2.VideoCapture("test_video.mp4")
        rc, img = self._video.read()
        if not rc:
            raise RuntimeError("Reading video frame failed")

        rc, self._last_frame = cv2.imencode(".jpg", img)
        if not rc:
            raise ValueError("Encoding frame failed.")

        self._metadata = {
            "ExposureTime": 0.0,
            "AnalogueGain": 0.0,
        }
        self._controls: dict[str, float | bool] = {
            "AeEnable": False,
            "ExposureValue": 0.0,
        }
        self._last_time = monotonic()

    def _update_frame(self) -> None:
        # if (monotonic() - self._last_time) > (1/24):
        rc, img = self._video.read()
        if not rc:
            self._video.set(2, 0)
            rc, img = self._video.read()
        # Internally, the image array is height X width.
        # But then the resize function expects us to provide width X height
        height, width, _ = img.shape
        img = cv2.resize(img, (640, int(640 / width * height)))
        rc, self._last_frame = cv2.imencode(".jpg", img)
        self._last_time = monotonic()

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
        self._update_frame()
        return bytes(self._last_frame)

    def take_photo(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        # FIXME: Include image metadata.
        self._update_frame()

        data: dict[str, Any] = {
            "cam_driver": "cv2",
            "metadata": self.get_metadata(),
            # "config": request.config, # FIXME: Get this working # noqa: E501,ERA001

            # FIXME: DO this with OpenCV
            "camera_properties": {},
            # "camera_properties": self._picam2.camera_properties
        }

        return data, bytes(self._last_frame), b""

    def get_metadata(self) -> dict[str, float]:
        """Get camera metadata.

        Returns:
            Camera metadata.

        """
        return self._metadata

    def get_controls(self) -> dict[str, float]:
        """Get camera controls.

        Returns:
            Camera Controls

        """
        return self._controls

    def set_controls(self, controls: dict[str, bool | float]) -> None:
        """Set camera controls.

        Arguments:
            controls: The camera controls to set.

        """
        self._controls = controls

    def set_exposure_time(self, time: float) -> None:
        """Set the exposure time.

        Arguments:
            time: The exposure time to set

        """
        self._controls["ExposureTime"] = time

    def set_gain(self, gain: float) -> None:
        """Set sensor gain.

        Arguments:
            gain: The sensor gain to set.

        """
        self._metadata["AnalogueGain"] = gain

    def set_ev(self, ev: float) -> None:
        """Set sensor exposure compensation.

        Arguments:
            ev: The exposure compensation to set.

        """
        self._controls["ExposureValue"] = ev

    def set_auto_exposure(self, ae: bool) -> None:
        """Enable/Disable auto-exposure.

        Arguments:
            ae: Whether or not to enable auto-exposure

        """
        self._controls["AeEnable"] = ae

    def get_exposure_time(self) -> float:
        """Get the exposure time.

        Returns:
            Exposure Time

        """
        return self._metadata["ExposureTime"]

    def get_gain(self) -> float:
        """Get sensor gain.

        Returns:
            Sensor Gain

        """
        return self._metadata["AnalogueGain"]

    def get_ev(self) -> float:
        """Get sensor exposure compensation.

        Returns:
            Exposure Compensation

        """
        return self._controls["ExposureValue"]

    def get_auto_exposure(self) -> bool:
        """Get whether or not auto-exposure is enabled.

        Returns:
            Whether or not auto-exposure is enabled

        """
        # Assertion helps with type hinting, so we are ok with it here
        assert isinstance(self._controls["AeEnable"], bool)  # noqa: S101
        return self._controls["AeEnable"]

    def close(self) -> None:
        """Shut down camera."""
        self._video.release()
