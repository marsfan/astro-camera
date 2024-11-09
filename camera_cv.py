#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Module for manipulating camera via OpenCV."""
import cv2

from camera_base import CameraBase

# TODO: Abstract base class for this and picamera

# TODO: Context manager suppot

# TODO: Metdata suport, exposure support


class Camera(CameraBase):
    """Class for manipulating camera via OpenCV."""

    def __init__(self) -> None:
        """Initialize camera."""
        self._capture = cv2.VideoCapture(0)

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
        rc, img = self._capture.read()
        rc, frame = cv2.imencode(".jpg", img)
        return bytes(frame)

    def take_photo(self) -> tuple[dict, bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG
        """
        # FIXME: Need to figure out how to encode DNG. Seems OpenCV
        # Does not have that by default.
        rc, img = self._capture.read()
        rc, jpg = cv2.imencode(".jpg", img)
        # FIXME: Include image metadata.

        data = {
            "cam_driver": "cv2",
            "metadata": self.get_metadata(),
            # "config": request.config, # FIXME: Get this working

            # FIXME: DO this with opencv
            "camera_properties": {}
            # "camera_properties": self._picam2.camera_properties
        }

        return data, bytes(jpg), bytes()

    def get_metadata(self) -> dict[str, float]:
        """Get camera metadata.

        Returns:
            Camera Metadata.

        """
        # FIXME: Figure out how to do this in opencv
        return {
            "ExposureTime": 0,
            "AnalogueGain": 0
        }

    def get_controls(self) -> dict[str, float]:
        """Get camera controls.

        Returns:
            Camera Controls

        """
        # FIXME: Figure out for opencv
        return {"AeEnable": False, "ExposureValue": 0.0}

    def set_controls(self, controls: dict[str, bool | float]) -> None:
        """Set camera controls.

        Arguments:
            controls: The camera controls to set.

        """
        # TODO: Figure out how to do this for opencv

    def close(self) -> None:
        """Shut down camera."""
        self._capture.release()
