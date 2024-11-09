#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Base module for all camera drivers."""

from abc import ABC, abstractmethod


class CameraBase(ABC):
    """Base class for interacting with a camera."""

    @abstractmethod
    def __init__(self) -> None:
        """Initialize camera."""

    @abstractmethod
    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """

    @abstractmethod
    def take_photo(self) -> tuple[dict, bytes, bytes]:
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
    def close(self) -> None:
        """Shut down camera."""
