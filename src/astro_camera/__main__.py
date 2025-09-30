#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from argparse import ArgumentParser


def main() -> None:
    """Run when called from command line."""
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
    args = parser.parse_args()

    if args.tool == "webui":
        raise NotImplementedError
    else:
        raise ValueError("Unknown tool")


if __name__ == "__main__":
    main()
