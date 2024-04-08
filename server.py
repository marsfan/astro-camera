#!/usr/bin/python3

# This is the same as mjpeg_server.py, but uses the h/w MJPEG encoder.

import io
import logging
import socketserver
from http import server
from threading import Condition
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import json
from typing import Any
from socket import socket


from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from picamera2.request import CompletedRequest


cam_controls = {"AeEnable": True}
picam2 = Picamera2()

preview_config = picam2.create_video_configuration(main={"size": (640, 480)}, controls=cam_controls)

picam2.configure(preview_config)

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

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


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
        cam_metadata = picam2.capture_metadata()

        with open("index.html", "rb") as file:
            content = Page(file.read())
        content.replace_tag("gain", str(cam_metadata["AnalogueGain"]))
        content.replace_tag("exposure", str(cam_metadata["ExposureTime"]))

        if cam_controls["AeEnable"] == True:
            content.replace_tag("autoEx", "checked=\"\"")
        else:
            content.replace_tag("autoEx", "")
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(bytes(content))


    def set_camera_props(self, requested: dict[str, str]) -> None:
        global cam_controls
        modified_controls: dict[str, Any] = {}
        if "exval" in requested:
            modified_controls["ExposureTime"] = float(requested["exval"][0])
        if "gainval" in requested:
            modified_controls["AnalogueGain"] = float(requested["gainval"][0])
        if "autoex" in requested and requested["autoex"][0] == "on":
            modified_controls["AeEnable"] = True
        else:
            modified_controls["AeEnable"] = False
        cam_controls = modified_controls
        picam2.set_controls(modified_controls)

    def take_photo(self) -> None:
        # Copy over metadata from preview mode that we want.
        controls = {}
        md = picam2.capture_metadata()
        controls["ExposureTime"] = (md["ExposureTime"])
        controls["AnalogueGain"] = (md["AnalogueGain"])
        # Create config for high res photo
        capture_config = picam2.create_still_configuration(raw={}, display=None, controls=controls)

        # Stop the encoder to prevent crashes
        picam2.stop_encoder()

        # Take the photo
        request: CompletedRequest = picam2.switch_mode_and_capture_request(capture_config)
        # FIXME: Filename by datestamp
        # filename = f"IMG_{datetime.isoformat(datetime.now())}"
        print(picam2.capture_metadata())

        # Save image as JPG, DNG, and the metadata
        filename="image"
        request.save("main", f"{filename}.jpg")
        request.save_dng(f"{filename}.dng")
        with open(f"{filename}.json", "w") as file:
            print(request.config)
            data = {
                "metadata": request.get_metadata(),
                # "config": request.config, # FIXME: Get this working
                "camera_properties": picam2.camera_properties
            }
            json.dump(data, file, indent=4)

        # Release the request
        request.release()

        # Restart MJPEG encoder
        picam2.start_encoder(MJPEGEncoder(), FileOutput(output))


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
            cam_metadata = picam2.capture_metadata()
            controls = picam2.camera_controls
            print(controls)
            print(cam_metadata)
            self.send_index_redir()
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
                    # FIXME: Replace with camera stream
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
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


output = StreamingOutput()
picam2.start_recording(MJPEGEncoder(), FileOutput(output))

try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()
