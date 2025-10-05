#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Module for manipulating camera via PiCamera2."""

from copy import deepcopy
from io import BufferedIOBase, BytesIO
from threading import Condition

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

from . import CameraBase


class StreamingOutput(BufferedIOBase):
    def __init__(self) -> None:
        self.frame = None
        self.condition = Condition()

    def write(self, buf: bytes | None) -> None:
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class PiCamera(CameraBase):
    """Class for manipulating camera via PiCamera2."""

    def __init__(self) -> None:
        """Initialize Camera."""
        # FIXME: Support initialization args for controls.
        # and preview config (namely size)
        self._cam_controls = {"AeEnable": True, "ExposureValue": 0.0}
        self._picam2 = Picamera2()

        self._preview_config = self._picam2.create_video_configuration(
            main={"size": (640, 480)},
            controls=self._cam_controls,
        )

        self._picam2.configure(self._preview_config)

        self._output = StreamingOutput()

        self._picam2.start_recording(MJPEGEncoder(), FileOutput(self._output))

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
        # TODO: Ensure we are using hw encoder
        # https://github.com/raspberrypi/picamera2/issues/752
        with self._output.condition:
            self._output.condition.wait()
            return self._output.frame

    def take_photo(self) -> tuple[dict, bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        # Copy over metadata from preview mode that we want.
        controls = {}
        controls["ExposureTime"] = self._cam_controls["ExposureTime"]
        controls["AnalogueGain"] = self._cam_controls["AnalogueGain"]
        controls["AeEnable"] = self._cam_controls["AeEnable"]
        controls["ExposureValue"] = self._cam_controls["ExposureValue"]

        # Create config for high res photo
        capture_config = self._picam2.create_still_configuration(
            raw={}, display=None, controls=controls)

        # Stop the encoder to prevent crashes
        # See https://forums.raspberrypi.com/viewtopic.php?t=354226
        self._picam2.stop_encoder()

        # Take the photo
        # FIXME: After it switches back, controls are defaults, not last
        # user specified values
        request = self._picam2.switch_mode_and_capture_request(
            capture_config,
        )

        # TODO: Encode bytes.
        # FIXME: Is there a way to do this without using a BytesIO?
        dng_buf = BytesIO()
        jpg_buf = BytesIO()
        request.save("main", jpg_buf, format="jpg")
        request.save_dng(dng_buf)
        data = {
            "cam_driver": "picamera2",
            "metadata": request.get_metadata(),
            # "config": request.config, # FIXME: Get this working # noqa: ERA001,E501
            "camera_properties": self._picam2.camera_properties,
        }
        # Rewind buffers so we can dump everything
        dng_buf.seek(0)
        jpg_buf.seek(0)

        # Release request
        request.release()

        # Restart MJPEG encoder
        self._picam2.start_encoder(MJPEGEncoder(), FileOutput(self._output))

        return data, jpg_buf.read(), dng_buf.read()

    def get_metadata(self) -> dict[str, float]:
        """Get camera metadata.

        Returns:
            Camera metadata.

        """
        return self._picam2.capture_metadata()

    def get_controls(self) -> dict[str, float]:
        """Get camera controls.

        Returns:
            Camera Controls

        """
        return self._picam2.camera_controls

    def set_controls(self, controls: dict[str, bool | float]) -> None:
        """Set camera controls.

        Arguments:
            controls: The camera controls to set.

        """
        self._cam_controls = controls

        # We need to change controls to allow for frame to take
        # longer than default. If we don't change this, controls will
        # be locked at lower value than we specified.
        # https://forums.raspberrypi.com/viewtopic.php?t=291474
        self._cam_controls["FrameDurationLimits"] = (
            0,
            controls["ExposureTime"] + 1000
        )

        # Setting preview controls, we want to clamp exposure time to
        # no more than 1/5 sec to maintain a useable framerate
        # FIXME: Need a way to indicate this on the UI.
        # UI probably needs a "current values" readout.
        preview_controls = deepcopy(controls)
        if "ExposureTime" in controls:
            preview_controls["ExposureTime"] = min(
                controls["ExposureTime"],
                200000
            )
            preview_controls["FrameDurationLimits"] = (
                0,
                controls["ExposureTime"] + 1000
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
        return self._cam_controls["ExposureValue"]

    def get_auto_exposure(self) -> bool:
        """Get whether or not auto-exposure is enabled.

        Returns:
            Whether or not auto-exposure is enabled

        """
        return self._cam_controls["AeEnable"]

    def close(self) -> None:
        """Shut down camera."""
        self._picam2.stop_recording()
