#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from argparse import ArgumentParser
from typing import Sequence

from .camera import CameraBase
from .camera.dummy import DummyCamera
from .camera.opencv_webcam import OpenCVWebcam
from .server import server_main

try:
    from .camera.picam import PicamCamera
except ImportError:
    PicamCamera = None


def main(args_in: Sequence[str] | None = None, webui_reload: bool = False) -> None:
    """Run when called from command line.

    Warning:
        The ``auto_reload`` parameter should not be used unless the
        function is directly called from a main guard, as the method
        used for auto-reloading does not work properly elsewhere

    Arguments:
        args_in: Optional sequence of arguments to use instead of
            of reading from the command line
        webui_reload: Enables auto-reloading of the webui when files are
            changed.

    """
    parser = ArgumentParser(description="Astrophotography Camera")

    # FIXME: Replace with subcommands?
    parser.add_argument(
        "tool",
        type=str,
        choices=["webui"],
        help="The tool to launch"
    )

    parser.add_argument(
        "--camera",
        "-c",
        choices=["picam", "webcam", "dummy"],
        default="picam",
        help="Type of camera to launch with."
    )
    args = parser.parse_args(args_in)

    if args.camera == "picam" and PicamCamera is None:
        raise RuntimeError(
            "picamera2 not found. Program is either not running on a "
            "Raspberry Pi, or the picamera2 module is not installed."
        )

    camera: CameraBase
    if args.camera == "picam" and PicamCamera is not None:
        camera = PicamCamera()
    elif args.camera == "webcam":
        camera = OpenCVWebcam()
    else:
        camera = DummyCamera()

    if args.tool == "webui":
        server_main(camera, webui_reload)
    else:
        raise ValueError("Unknown tool")


if __name__ == "__main__":
    main()
