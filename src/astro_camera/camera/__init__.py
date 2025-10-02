#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Base module for all camera drivers."""

from abc import ABC, abstractmethod
from typing import Any


class CameraBase(ABC):
    """Base class for interacting with a camera."""

    @abstractmethod
    def __init__(self) -> None:
        """Initialize camera."""

    @abstractmethod
    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        The output from should have a width of 640 pixels, to keep
        preview size and network use low.

        Returns:
            Single frame for display.

        """

    @abstractmethod
    def take_photo(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """

    @abstractmethod
    def get_metadata(self) -> dict[str, float]:
        """Get camera metadata.

        Returns:
            Camera metadata.

        """

    @abstractmethod
    def get_controls(self) -> dict[str, float]:
        """Get camera controls.

        Returns:
            Camera Controls

        """

    @abstractmethod
    def set_controls(self, controls: dict[str, bool | float]) -> None:
        """Set camera controls.

        Arguments:
            controls: The camera controls to set.

        """

    @abstractmethod
    def set_exposure_time(self, time: float) -> None:
        """Set the exposure time.

        Arguments:
            time: The exposure time to set

        """

    @abstractmethod
    def set_gain(self, gain: float) -> None:
        """Set sensor gain.

        Arguments:
            gain: The sensor gain to set.

        """

    @abstractmethod
    def set_ev(self, ev: float) -> None:
        """Set sensor exposure compensation.

        Arguments:
            ev: The exposure compensation to set.

        """

    @abstractmethod
    def set_auto_exposure(self, ae: bool) -> None:
        """Enable/Disable auto-exposure.

        Arguments:
            ae: Whether or not to enable auto-exposure

        """

    @abstractmethod
    def get_exposure_time(self) -> float:
        """Get the exposure time.

        Returns:
            Exposure Time

        """

    @abstractmethod
    def get_gain(self) -> float:
        """Get sensor gain.

        Returns:
            Sensor Gain

        """

    @abstractmethod
    def get_ev(self) -> float:
        """Get sensor exposure compensation.

        Returns:
            Exposure Compensation

        """

    @abstractmethod
    def get_auto_exposure(self) -> bool:
        """Get whether or not auto-exposure is enabled.

        Returns:
            Whether or not auto-exposure is enabled

        """

    @abstractmethod
    def close(self) -> None:
        """Shut down camera."""
