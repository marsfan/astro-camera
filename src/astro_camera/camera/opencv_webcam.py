#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Module for manipulating camera via OpenCV."""
import subprocess
import sys
import time
from threading import Condition, Event, Thread, current_thread
from typing import TYPE_CHECKING, Any

import cv2

if TYPE_CHECKING:
    from cv2.typing import MatLike

from . import CameraBase

# TODO: Context manager suppot
# TODO: Metdata suport, exposure support
# FIXME: Try setting camera to use MJPG fourCC. If it works, the camera
# has built in MJPG encoder we could use instead.
# Something like this:
# fourcc = cv2.VideoWriter_fourcc(*"MJPG")
# camera.set(cv2.CAP_PROP_FOURCC, fourcc)
# assert fourcc == camera.get(cv2.CAP_PROP_FOURCC)
# camera.set(cv2.CAP_PROP_CONVERT_RGB, 0)
# On linux, we can list supported fourcc with `v4l2-ctl --device=/dev/video0 --list-formats-ext`
# Also can list all info about device with `v4l2-ctl --device=/dev/video0 --all`

# TODO: Support exposure, gain, etc
# cv2.CAP_PROP_EXPOSURE controlss exposure. Small number is longer exposure (IDK why)
# Seems to range from 0 to 10000 in steps of 10?

# cv2.CAP_PROP_GAIN seems to have no effect?


class CameraThread(Thread):
    """Thread for reading from the camera."""

    def __init__(self, camera_index: int) -> None:
        """Initialize the camera, and the thread.

        Thread is not yet started. We have just initialized things.
        call :py:meth:`start` to start the thread.

        """
        super().__init__(name="CV2 Webcamera")
        self._camera_index = camera_index
        self._capture: cv2.VideoCapture | None = None
        self.image_condition = Condition()
        self._running = Event()
        self.full_photo: None | MatLike = None
        self.frame: None | MatLike = None

    def run(self) -> None:
        """Main logic for the thread.

        This should not be called directly. Instead :py:meth:`start`
        should be called.

        """
        self._capture = cv2.VideoCapture(self._camera_index)
        # FIXME: Figure out how to do this in OpenCV/python
        # The webcam I'm using has some sort of dynamic framerate linked
        # to exposure. I can get good framerates with camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        # But then I have to handle controlling things myself.
        # Instead, I can use this command to take manual control and it seems to work out OK
        # It still sort of manual, but brightness looks better.
        # Per RPI forums, this is to let the AE algorithm slow the exposure
        # time down to levels that hurt frame rate.
        # forums.raspberrypi.com/viewtopic.php?t=206708
        if sys.platform == "linux":
            subprocess.run(
                [
                    "/usr/bin/v4l2-ctl",
                    "--device=/dev/video0",
                    "--set-ctrl",
                    "exposure_dynamic_framerate=0",
                ],
                check=True,
                shell=False,
            )

        self._running.set()
        while self._running.is_set():
            rc, img = self._capture.read()
            if not rc:
                raise RuntimeError("Failed to read frame.")
            rc, full_jpg = cv2.imencode(".jpg", img)
            if not rc:
                raise RuntimeError("Failed to encode full image.")
            height, width, _ = img.shape
            scaled = cv2.resize(
                img,
                (640, int(640 / width * height)),
            )
            rc, scaled_jpg = cv2.imencode(".jpg", scaled)
            if not rc:
                raise RuntimeError("Failed to encode preview image")
            with self.image_condition:
                self.full_photo = full_jpg
                self.frame = scaled_jpg
                self.image_condition.notify_all()

            # If we ran without a sleep, this thread could take up a lot
            # of unnecessary CPU resources.
            # So we are going to sleep for a little bit. This means the
            # theoretical max frame rate is 100FPS, which is more than
            # we care about, but its enough to ensure the thread is not
            # going crazy on CPU use
            time.sleep(0.01)

        # Close camera
        self._capture.release()

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        Raise:
            TypeError: Raised if the photo was none when trying to
                return it.

        """
        with self.image_condition:
            self.image_condition.wait()
            if self.frame is None:
                raise TypeError("Frame was none")
            return bytes(self.frame)

    def get_photo(self) -> bytes:
        """Get the full sized image.

        Returns:
            Bytes for the JPEG of the full sized image.

        Raise:
            TypeError: Raised if the photo was none when trying to
                return it.

        """
        with self.image_condition:
            self.image_condition.wait()
            if self.full_photo is None:
                raise TypeError("Frame was None")
            return bytes(self.full_photo)

    def stop(self) -> None:
        """Tell the thread to stop.

        This clears a flag to cause the thread to stop running.

        If this method is called from a different thread than the
        the instance it operates on, it will also then join the thread,
        blocking execution until it has been properly shut down.

        """
        self._running.clear()
        if current_thread != self:
            self.join()


class OpenCVWebcam(CameraBase):
    """Class for manipulating camera via OpenCV."""

    def __init__(self) -> None:
        """Initialize camera."""
        # FIXME: Need a way to select the correct index.
        # On laptop, built in webcam tends to be index 0,
        # Then things jump around a bit on the PI
        self._camera_thread = CameraThread(0)

    def initialize_hw(self) -> None:
        """Initialize the camera hardware."""
        self._camera_thread.start()

    def get_frame(self) -> bytes:
        """Get a single frame for real-time streaming.

        Returns:
            Single frame for display.

        """
        return self._camera_thread.get_frame()

    def take_photo(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        # FIXME: Look into supporting switching modes like in picam2
        data: dict[str, Any] = {
            "cam_driver": "cv2",
            "metadata": self.get_metadata(),
            # "config": request.config, # FIXME: Get this working # noqa: ERA001,E501

            # FIXME: DO this with OpenCV
            "camera_properties": {},
            # "camera_properties": self._picam2.camera_properties
        }

        # FIXME: Need to figure out how to encode DNG. Seems OpenCV
        # Does not have that by default.
        return data, self._camera_thread.get_photo(), b""

    async def take_photo_async(self) -> tuple[dict[str, Any], bytes, bytes]:
        """Take a single high-resolution photo.

        Returns:
            Three element tuple:
                * Image metadata
                * Image in JPG
                * Image in DNG

        """
        # FIXME: Look into supporting switching modes like in picam2
        data: dict[str, Any] = {
            "cam_driver": "cv2",
            "metadata": self.get_metadata(),
            # "config": request.config, # FIXME: Get this working # noqa: ERA001,E501

            # FIXME: DO this with OpenCV
            "camera_properties": {},
            # "camera_properties": self._picam2.camera_properties
        }

        # FIXME: Need to figure out how to encode DNG. Seems OpenCV
        # Does not have that by default.
        return data, self._camera_thread.get_photo(), b""

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
        self._camera_thread.stop()
