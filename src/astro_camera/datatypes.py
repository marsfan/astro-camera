#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Data types for the program."""
from typing import Any, Literal, TypedDict

from libcamera import ColorSpace, Rectangle, Transform, controls

# TODO: Submit typings to picamera2 repo?


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

    ColorFilterArrangement: int  # TODO: Enum for translating this.
    """Sensor Bayer Order."""

    Location: int  # TODO: enum for tranlsating this
    """Location on the device. Unused by Raspberry Pi"""

    Model: str
    """Name the sensor advertises itself as."""

    PixelArrayActiveAreas: tuple[int, int, int, int]
    """Active area of the pixel array.

    Is in the form (x offset, y offset, width, height).
    """

    PixelArraySize: tuple[int, int]
    """Size of the sensors active pixel area in (x, y)."""

    Rotation: int
    """Rotation of sensor relative to camera board in degrees.

    Many RPi sensors are mounted upside down (i.e. 180degrees)

    """

    ScalerCropMaximum: tuple[int, int, int, int]
    """Area within active area that will be read out by the camera in its current mode.

    In the form (x_offset, y_offset, width, height)

    """

    SensorSensitivity: float
    """relative sensitivity of current camera mode compared to other modes."""

    UnitCellSize: tuple[int, int]
    """Sensor Pixel size in (x, y) nanometers."""


class CameraControls(TypedDict):
    """Runtime controls for the camera.

    Controls can be set in initial configuration, before starting the
    camera, or during camera running using the
    :py:meth:`Picamera.set_controls` method

    Note:
        Not all members may be present for a given camera.
        Checking for existence is recommended.

    """

    AeConstraintMode: controls.AeConstraintModeEnum
    """Constraint Mode of the AEC/AGC algorithm."""

    AeEnable: bool  # FIXME: Seems to be a 3 element tuple?
    """Turn the AEC/AGC algorithm on and off."""

    AeExposureMode: controls.AeExposureModeEnum
    """Exposure mode of the AEC/AGC algorithm."""

    AeFlickerMode: controls.AeFlickerModeEnum
    """Flicker avoidance mode of the AEC/AGC algorithm."""

    AeFlickerPeriod: int
    """Flicker Period in microseconds."""

    AeMeteringMode: controls.AeMeteringModeEnum
    """Metering mode of the AEC/AGC algorithm."""

    AfMetering: controls.AfMeteringEnum
    """Where focus should be measured."""

    AfMode: controls.AfModeEnum
    """Autofocus Mode."""

    AfPause: controls.AfPauseEnum
    """Pause continuous autofocus.

    Only has an effect when in continuous autofocus mode.

    """

    AfRange: controls.AfRangeEnum
    """Range of lens positions to search."""

    AfSpeed: controls.AfSpeedEnum
    """Speed of autofocus search."""

    AfTrigger: controls.AfTriggerEnum
    """Start an autofocus cycle."""

    AfWindows: list[tuple[int, int, int, int]]
    """Location of windows in the image to use for measuring focus.

    This should be a list of rectangles in the image. Each rectangle is
    represented by a tuple of [x_offset, y_offset, width, height].

    Rectangles refer to the maximum scaler crop window.
    See :py:attr:`CameraProperties.ScalerCropMaximum`

    """

    AnalogueGain: Any  # TODO: Add correct type hint
    "Consult the camera_controls property."

    AwbEnable: bool  # FIXME: Seems to be 3 element tuple?
    """Turn on or off the auto white balance algorithm."""

    AwbMode: controls.AwbModeEnum
    """Set the mode of the AWB algorithm."""

    Brightness: float
    """Adjust image brightness from -1.0 to 1.0."""

    ColourCorrectionMatrix: tuple[float, float, float,
                                  float, float, float,
                                  float, float, float]
    """3x3 matrix used by the ISP to convert raw camera colors to sRGB.

    This is Read Only

    """

    ColourGains: tuple[float, float]
    """Pair of color gains. First number is red gain, second is blue gain.

    Setting this will disable AWB.

    """

    ColourTemperature: int
    """Estimate of the color temperature in Kelvin of the current image.

    This is Read Only.

    """

    Contrast: float
    """The contrast of the image.

    0.0: No Contrast
    1.0: Default "normal" contrast.
    Larger numbers increase contrast proportionately.

    """

    DigitalGain: float
    """Digital gain to apply to image.

    This cannot be set directly. Set
    :py:attr:`CameraControls.AnalogueGain` and this will be updated to
    add any additional gain that is needed.

    """

    ExposureTime: Any  # FIXME: Consult camera_controls property
    """Sensor Exposure time in microseconds."""

    ExposureValue: float
    """The exposure compensation in "stops"

    Value should be between -8.0 and 8.0.

    Negative values decrease brightness, positive values increase it.
    0.0 is the base or "normal" value.

    """

    FrameDuration: int
    """Amount of time in us since previous camera frame.

    Only found in image metadata. Framerate should be changed with the
    :py:attr:`CameraControls.FrameDurationLimits` control.

    """

    FrameDurationLimits: Any  # TODO: consult the camera_controls property
    """Min and Max time (in us) that the sensor can take to deliver a frame."""

    HdrChannel: controls.HdrChannelEnum
    """Which HDR Channel the current frame represents. Read Only."""

    HdrMode: controls.HdrModeEnum
    """Whether to run the camera in HDR mode, and in which mode.

    This is not the in-camera HDR support by the Camera Module 3

    Mostly only supported by the Pi 5 or later devices.

    """

    LensPosition: float
    """Position of the lens in dioptres.

    Dioptres are the reciprocal of the distance in meters.

    """

    Lux: int
    """Estimate of the scene brightness in lux. Read only."""

    NoiseReductionMode: controls.draft.NoiseReductionModeEnum
    """The noise reduction mode to use.

    Normally Picamera2 will select an appropriate mode automatically.

    """

    Saturation: float
    """Color saturation to use. Max of 32

    0.0: Grayscale
    1.0: Normal color
    Higher values produce more saturated colors.

    """

    ScalerCrop: Rectangle
    """The portion of the image received from the sensor that will be saved."""

    SensorTimestamp: int
    """Time the frame was produced by the sensor in nanoseconds since boot.

    This option is read only.

    """

    SensorBlackLevels: tuple[int, int, int, int]
    """The black levels of the raw sensor image. Read Only."""

    Sharpness: float
    """Sharpness of the image. Max of 16.0.

    0.0: No sharpening
    1.0: Normal sharpening.
    Higher leads to more sharpening.

    """

    # FIXME: Finish writing this, see Picamera document
    # FIXME: Indicate they might not be present. Need to check typing docs


class SensorMode(TypedDict):
    """Information about a sensor mode for a PiCamera."""

    format: str
    """The sensor format.

    This can be passed directly to :py:attr:`StreamConfig.format`
    when configuring a camera.

    """

    unpacked: str
    """The unpacked sensor format."""

    bit_depth: int
    """The number of bits in each sample."""

    size: tuple[int, int]
    """The image size in pixels.

        This can be passed directly to :py:attr:`StreamConfig.size` when
    configuring a camera.

    """

    fps: float
    """Maximum frame rate for this mode."""

    crop_limits: tuple[int, int, int, int]
    """Exact field of view of this mode within the full sensor output."""

    exposure_limits: tuple[int, int, int]
    """Min, Max, and default exposure time (in microseconds) for this mode.

    Note:
        On the HQ camera, the 1.8v XVS pin can be used for even longer
        exposures.

    """


class StreamConfiguration(TypedDict):
    """Picamera2 stream configuration."""

    size: tuple[int, int]
    """Image Dimensions."""

    format: str  # TODO: literal?
    """Image format. Must be YUV420 on RPi 4 and older"""

    # FIXME: Indicate this is not user controllable. Need to check typing docs
    stride: int
    """Length of each row in the image in bytes (read only)."""

    # FIXME: Indicate this is not user controllable. Need to check typing docs
    framesize: int
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
    """Number of buffers to allocate for camera stream."""

    queue: bool
    """Whether system can queue up a frame ready for a capture request."""

    sensor: SensorConfiguration
    """Parameters for configuring sensor operating mode.

    Members should be copied from values in the SensorMode typed dict.
    """

    # FIXME: raw might not be ok
    display: Literal["main", "lowres", "raw"] | None
    """Names of the streams to show in preview window."""

    # FIXME: raw might not be ok
    encode: Literal["main", "lowres", "raw"] | None
    """Names of the streams to encode if a video encoding is started."""

    controls: CameraControls
    """Initial values to set to camera run time controls."""

    lores: StreamConfiguration | None
    """Configuration options for the low resolution stream."""

    main: StreamConfiguration
    """Configuration options for the main image stream."""

    raw: StreamConfiguration  # FIXME: Might be optional?
    """Configuration options for the raw image stream."""

    use_case: str
    """Indicates the intended use case of the generated configuration."""
