#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Dummy camera driver, using a video to simulate a camera."""


import cv2

from camera_base import CameraBase
from time import monotonic


class Camera(CameraBase):
    """Base class for interacting with a camera."""

    def __init__(self) -> None:
        """Initialize camera."""

        self._video = cv2.VideoCapture("test_video.mp4")
        rc, img = self._video.read()

        rc, self._last_frame = cv2.imencode(".jpg", img)

        self._metadata = {
            "ExposureTime": 0,
            "AnalogueGain": 0
        }
        self._controls = {"AeEnable": False, "ExposureValue": 0.0}
        self._last_time = monotonic()

    def _update_frame(self) -> None:
        if (monotonic() - self._last_time) > (1/24):
            rc, img = self._video.read()
            if not rc:
                self._video.set(2, 0)
            rc, self._last_frame = cv2.imencode(".jpg", img)
            self._last_time = monotonic()

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
        self._update_frame()
        return bytes(self._last_frame)

    def take_photo(self) -> tuple[dict, bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG
        """
        # FIXME: Include image metadata.
        self._update_frame()

        data = {
            "cam_driver": "cv2",
            "metadata": self.get_metadata(),
            # "config": request.config, # FIXME: Get this working

            # FIXME: DO this with opencv
            "camera_properties": {}
            # "camera_properties": self._picam2.camera_properties
        }

        return data, bytes(self._last_frame), bytes()

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

    def close(self) -> None:
        """Shut down camera."""
        self._video.release()
