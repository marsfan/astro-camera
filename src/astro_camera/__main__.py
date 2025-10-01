#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from argparse import ArgumentParser
from typing import Sequence

from src.astro_camera.server import server_main


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

    if args.tool == "webui":
        server_main(webui_reload)
    else:
        raise ValueError("Unknown tool")


if __name__ == "__main__":
    main()
