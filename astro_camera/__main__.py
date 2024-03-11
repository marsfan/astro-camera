from picamera2 import Picamera2
from picamera2.request import CompletedRequest
from pprint import pprint
from pathlib import Path
from libcamera import controls
import json
# Picamera2.set_logging(Picamera2.DEBUG)
picam2 = Picamera2()

preview_config = picam2.create_preview_configuration(lores={"size": (340, 480), "format": "YUV420"})
camera_config = picam2.create_still_configuration(raw={}, display=None)

picam2.configure(preview_config)

picam2.start()

input("Press enter to capture")
request: CompletedRequest  =picam2.switch_mode_and_capture_request(camera_config)


request.save("main", "image.jpg")
request.save_dng("image.dng")
with open("image.metadata.json", "w") as file:
    json.dump(request.get_metadata(), file)
request.release()


# picam2.controls["AeConstraintModeEnum"] = "Normal"
# picam2.set_controls({"AeConstraintMode": "Normal"})
# pprint(picam2.camera_controls)
