#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Module for manipulating camera via PiCamera2."""

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from picamera2.request import CompletedRequest
from threading import Condition
from io import BytesIO

from camera_base import CameraBase


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class Camera(CameraBase):
    """Class for manipulating camera via PiCamera2."""

    def __init__(self) -> None:
        """Initialize Camera."""

        # FIXME: Support initialization args for controls.
        # and preview config (namely size)
        self._cam_controls = {"AeEnable": True, "ExposureValue": 0.0}
        self._picam2 = Picamera2()

        # FIXME:
        self._preview_config = picam2.create_video_configuration(
            main={"size": (640, 480)},
            controls=self._cam_controls
        )

        self._picam2.configure(self._preview_config)

        self._output = StreamingOutput()

        self._picam2.start_recording(MJPEGEncoder(), FileOutput(self._output))

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
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
        md = self.get_metadata()
        controls["ExposureTime"] = md["ExposureTime"]
        controls["AnalogueGain"] = md["AnalogueGain"]
        controls["AeEnable"] = self._cam_controls["AeEnable"]
        controls["ExposureValue"] = self._cam_controls["ExposureValue"]

        # Create config for high res photo
        capture_config = self._picam2.create_still_configuration(
            raw={}, display=None, controls=controls)

        # Stop the encoder to prevent crashes
        # See https://forums.raspberrypi.com/viewtopic.php?t=354226
        self._picam2.stop_encoder()

        # Take the photo
        request: CompletedRequest = self._picam2.switch_mode_and_capture_request(
            capture_config
        )

        # TODO: Encode bytes.
        # FIXME: Is there a way to do this without using a bytesio?
        dng_buf = BytesIO()
        jpg_buf = BytesIO()
        request.save("main", jpg_buf)
        request.save_dng(dng_buf)
        data = {
            "cam_driver": "picamera2",
            "metadata": request.get_metadata(),
            # "config": request.config, # FIXME: Get this working
            "camera_properties": self._picam2.camera_properties
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

    def close(self) -> None:
        """Shut down camera."""
        self._picam2.stop_recording()
