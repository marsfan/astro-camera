#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Web server for the camera system."""

import logging
import socketserver
from http import server
from time import sleep
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import json
from typing import Any
from socket import socket
from pathlib import Path

DUMMY_CAMERA = True

if DUMMY_CAMERA:
    from camera_dummy import Camera
else:
    try:
        from camera_picam import Camera
    except ImportError:
        from camera_cv import Camera

camera = Camera()


class Page:
    """Custom string with additional useful methods."""

    def __init__(self, val: bytes | str) -> None:
        """Initialize the page property.

        Arguments:
            val: The value of the page string.

        """
        if isinstance(val, str):
            self.value = bytes(val, "utf8")
        else:
            self.value = val

    def replace_tag(self, tag: str, new_val: str) -> None:
        """Replace the given tag in the page contents.

        Arguments:
            tag: The name of the tag to replace
            new_val: The value to insert into the tag.
        """
        tag = b"{{" + bytes(tag, "utf-8") + b"}}"
        self.value = self.value.replace(tag, bytes(new_val, "utf8"))

    def __bytes__(self) -> bytes:
        return self.value

    def __str__(self) -> str:
        return self.value.decode("utf-8")

    def __repr__(self) -> str:
        return repr(self.value)

    def __len__(self) -> int:
        return len(self.value)


class StreamingHandler(server.BaseHTTPRequestHandler):

    def __init__(self, request: socket | tuple[bytes, socket], client_address: Any, server: socketserver.BaseServer) -> None:
        super().__init__(request, client_address, server)

    def send_index_redir(self) -> None:
        """Send a HTTP 303 (See Other) to reload homepage."""
        self.send_response(303)
        self.send_header("Location", "/index.html")
        self.end_headers()

    def parse_opts(self) -> dict[str, str]:
        """Parse the options sent in the URL.

        Returns:
            Dictionary of the options sent in the URL.

        """
        return parse_qs(urlparse(self.path).query)

    def send_index(self) -> None:
        """Send the index.html page."""

        cam_metadata = camera.get_metadata()

        with open("index.html", "rb") as file:
            content = Page(file.read())
        content.replace_tag("gain", str(cam_metadata["AnalogueGain"]))
        content.replace_tag("exposure", str(cam_metadata["ExposureTime"]))
        content.replace_tag(
            "currentEv",
            str(camera.get_controls()["ExposureValue"])
        )

        if camera.get_controls()["AeEnable"] == True:
            content.replace_tag("autoEx", "checked=\"\"")
        else:
            content.replace_tag("autoEx", "")
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(bytes(content))

    def set_camera_props(self, requested: dict[str, str]) -> None:
        modified_controls: dict[str, Any] = {}
        if "exval" in requested:
            modified_controls["ExposureTime"] = float(requested["exval"][0])
        if "gainval" in requested:
            modified_controls["AnalogueGain"] = float(requested["gainval"][0])
        if "autoex" in requested and requested["autoex"][0] == "on":
            modified_controls["AeEnable"] = True
        else:
            modified_controls["AeEnable"] = False
        if "ev" in requested:
            modified_controls["ExposureValue"] = float(requested["ev"][0])
        camera.set_controls(modified_controls)

    def take_photo(self) -> None:
        """Take a high-resolution photo."""

        camera_data, jpg_photo, dng_photo = camera.take_photo()

        filename = f"IMG_{datetime.isoformat(datetime.now())}".replace(":", "_")  # noqa
        Path(f"{filename}.jpg").write_bytes(jpg_photo)
        Path(f"{filename}.dng").write_bytes(dng_photo)
        with Path(f"{filename}.json").open("w", encoding="UTF-8") as file:
            json.dump(camera_data, file, indent=4)

    def do_GET(self):
        """Process HTTP GET request."""
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path.startswith("/take?"):
            self.send_index_redir()
            self.take_photo()

        elif self.path.startswith("/exposure?"):
            self.send_index_redir()
            args = self.parse_opts()
            self.set_camera_props(args)
        elif self.path.startswith("/debug"):
            print(camera.get_controls())
            print(camera.get_metadata())
            self.send_index_redir()
        elif self.path.startswith("/reset"):
            self.send_index_redir()
            camera.set_controls({"AeEnable": True, "ExposureValue": 0.0})
        elif self.path == '/index.html':
            self.send_index()
        elif self.path == "/favicon.ico":
            self.send_response(200)
            self.send_header('Content-Type', 'image/x-icon')
            self.send_header('Content-Length', 0)
            self.end_headers()
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header(
                'Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    frame = camera.get_frame()
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Content-Length', 13)
                    self.end_headers()
                    self.wfile.write(b"\r\n")
                    sleep(0.1)
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


try:
    address = ('', 8000)
    page_server = StreamingServer(address, StreamingHandler)
    page_server.serve_forever()
finally:
    camera.close()
