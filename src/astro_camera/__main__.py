#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Command line interface for the program."""
from argparse import ArgumentParser
from collections.abc import Sequence
from typing import TYPE_CHECKING

from .camera.dummy import DummyCamera
from .camera.opencv_webcam import OpenCVWebcam
from .server import server_main

if TYPE_CHECKING:
    from .camera import CameraBase

try:
    from .camera.picam import PiCamera
except ImportError:
    PiCamera = None


def main(
        args_in: Sequence[str] | None = None,
        *,
        webui_debug: bool = False,
) -> None:
    """Run when called from command line.

    Warning:
        The ``debug`` parameter should not be used unless the
        function is directly called from a main guard, as the method
        used for auto-reloading does not work properly elsewhere

    Arguments:
        args_in: Optional sequence of arguments to use instead of
            of reading from the command line
        webui_debug: Enables auto-reloading of the webui when files are
            changed, and auto-open the webui on program start

    """
    parser = ArgumentParser(description="Astrophotography Camera")

    # FIXME: Replace with subcommands?
    parser.add_argument(
        "tool",
        type=str,
        choices=["webui"],
        help="The tool to launch",
    )

    parser.add_argument(
        "--camera",
        "-c",
        choices=["picam", "webcam", "dummy"],
        default="picam",
        help="Type of camera to launch with.",
    )
    args = parser.parse_args(args_in)

    camera: CameraBase
    if args.camera == "picam":
        if PiCamera is None:
            raise RuntimeError(
                "picamera2 not found. Program is either not running on a "
                "Raspberry Pi, or the picamera2 module is not installed.",
            )
        camera = PiCamera()
    elif args.camera == "webcam":
        camera = OpenCVWebcam()
    else:
        camera = DummyCamera()

    if args.tool == "webui":
        server_main(camera, debug=webui_debug)
    else:
        raise ValueError("Unknown tool")


if __name__ == "__main__":
    main()
