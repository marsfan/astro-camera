#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Simple script to launch the astro camera in WebUI mode with auto-reloading.

Because auto-reload has to be disabled when launching the program as as
module/application, this is needed to allow rapid development of the UI.

"""
from astro_camera.__main__ import main

if __name__ in {"__main__", "__mp_main__"}:
    main(webui_reload=True)
