#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Data types for the program."""
from typing import Optional, TypedDict
from libcamera import Transform, ColorSpace
from typing import Any, Literal
# TODO: Submit typings to Raspi repo

class Options(TypedDict):
    """Options for saving images.

    Can be set using the :py:attr:`Picamera2.options` attribute.

    """

    quality: int
    """JPEG Quality Level from 0 to 95."""

    compress_level: int
    """PNG Compression level from 0 to 9."""

class CameraProperties(TypedDict):
    """Information about the sensor being used.

    Accessed by the :py:attr:`Picamera2.camera_properties` property.

    """
    # FIXME: Finish writing this, see Picameara document


class CameraControls(TypedDict):
    """Runtime controls for the camera.

    Controls can be set in initial configuration, before starting the
    camera, or during camera running using the :py:meth:`Picamera.set_controls` method

    Note:
        Not all memebrs may be present for a given camera.
        Checking for existince is recommended.

    """
    # FIXME: Finish writing this, see Picameara document
    # FIXME Indicate they might nott be present. Need to check typing docs

class SensorMode(TypedDict):
    """Picamera2 sensor mode information."""

    bit_depth: int
    """Number of bits per pixel"""

    crop_limits: tuple[int, int, int, int]
    """Actual field of view for the mode."""

    # NOTE: On HQ camera, attaching to the 1.8v XVS pin can allow for even longer exposures.
    # See https://forums.raspberrypi.com/viewtopic.php?t=347476
    exposure_limits: tuple[int, int]
    """Minimum and maximum allowed exposure time in microseconds."""

    format: str # TODO: Proper reference to sstreamconfig in docstring
    """Packed sensor format. Can be passed to raw stream format field."""

    fps: float
    """Maximum supported framerate for the mode"""

    size: tuple[int, int] # TODO: Proper reference to sstreamconfig in docstring
    """Sensor output resolution. Can be passed to the 'size' parameter for a stream."""

    unpacked: str
    """Unpacked Raw format for the mode. Use in place of 'format' of unpacked raws are required."""

class StreamConfiguration(TypedDict):
    """Picamera2 stream configuration."""

    size: tuple[int, int]
    """Image Dimensions."""

    format: str  # TODO: literal?
    """Image format. Must be YUV420 on RPi 4 and older"""

    stride: int  # FIXME: Indicate this is not user controllable. Need to check typing docs
    """Length of each row in the image in bytes (read only)."""

    framesize: int # FIXME: Indicate this is not user controllable. Need to check typing docs
    """Total amount of memory the image will occupy (read only)."""

class SensorConfiguration(TypedDict):
    """Picamera 2 sensor configuration."""

    output_size: tuple[int, int]
    """Resolution of the sensor mode."""

    bit_depth: int
    """Bit depth of the sensor mode."""

class CameraConfiguration(TypedDict):
    """Picamera2 Camera Configuration dictionary."""

    transform: Transform
    """Transformations to apply to the image."""

    colour_space: ColorSpace
    """The color space of output images."""

    buffer_count: int
    """Number of bufffers to allocate for camera stream."""

    queue: bool
    """Whether system can queue up a frame ready for a capture request."""

    sensor: SensorConfiguration
    """Parameters for configuring sensor operating mode.

    Members should be copied from values in the SensorMode typed dict.
    """

    display: Optional[Literal["main", "lowres", "raw"]]  # FIXME: raw might not be ok
    """Names of the streams to show in preview window."""

    encode: Optional[Literal["main", "lowres", "raw"]] # FIXME: raw might not be ok
    """Names of the streams to encode if a video encoding is started."""

    controls: CameraControls
    """Initial values to set to camera run time controls."""

    lores: Optional[StreamConfiguration]
    """Configuration options for the low resolution stream."""

    main: StreamConfiguration
    """Configuration options for the main image stream."""

    raw: StreamConfiguration # FIXME: Might be optional?
    """Configuration options for the raw image stream."""

    use_case: str
    """Indicates the inteded use case of the generated configuration."""