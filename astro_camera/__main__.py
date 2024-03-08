from picamera2 import Picamera2
from pprint import pprint
from pathlib import Path
# Picamera2.set_logging(Picamera2.DEBUG)
picam2 = Picamera2()

camera_config = picam2.create_still_configuration(lores={"size": (340, 480), "format": "YUV420"})

picam2.configure(camera_config)

picam2.start()
picam2.capture_file(Path("test.jpg"))
# Capture_metadata waits on a new frame to arrive
pprint(picam2.capture_metadata())