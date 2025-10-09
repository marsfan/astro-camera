#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Helper for tracing the server with viztracer."""
import sys

from viztracer import VizTracer

from astro_camera.camera.dummy import DummyCamera
from astro_camera.server import server_main

try:
    from astro_camera.camera.picam import PiCamera
except ImportError:
    # If the PiCamera module fails to load, we are probably running
    # on non-rpi hardware. If the user requests using RPI camera
    # hardware, we will later raise an exception.
    # Suppressions needed here because mypy does handle the
    # use of setting an import's type
    # FIXME: Can we move this checking into the PiCamera module
    # instead, so the error is raised on construction of instance?
    PiCamera = None  # type: ignore[assignment,misc]


def main() -> None:
    """Run web server and trace."""
    # TODO: Add plugins?
    tracer = VizTracer(
        tracer_entries=10000000,
        minimize_memory=True,
        # log_async=True
    )

    if "picamera" in sys.argv:
        camera = PiCamera()
    else:
        camera = DummyCamera()
    with tracer:
        server_main(camera=camera)


if __name__ == "__main__":
    main()
