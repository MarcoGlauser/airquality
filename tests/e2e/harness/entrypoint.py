"""Container entrypoint for e2e tests: start the emulated hardware, then run the real app."""

import os
import runpy
import sys

sys.path.insert(0, "/harness")
import serial_emulators  # noqa: E402

serial_emulators.start()

os.chdir("/app")
sys.path.insert(0, "/app")
sys.argv = ["main.py"]
runpy.run_path("/app/main.py", run_name="__main__")
