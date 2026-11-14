"""Serial sensor emulators for the e2e container.

Each emulator owns a pseudo-terminal and links its slave end to the device path the
app opens, so pyserial and the app's protocol code talk to it like real hardware.

The test runner steers the emulators through /harness-state/control.json and reads
what they saw from /harness-state/events.jsonl.
"""

import json
import os
import threading
import time
import tty

STATE_DIR = "/harness-state"
CONTROL_FILE = os.path.join(STATE_DIR, "control.json")
EVENTS_FILE = os.path.join(STATE_DIR, "events.jsonl")

_events_lock = threading.Lock()


def control():
    try:
        with open(CONTROL_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def log_event(device, event, **data):
    with _events_lock, open(EVENTS_FILE, "a") as f:
        f.write(json.dumps({"device": device, "event": event, **data}) + "\n")


def open_pty(device_path):
    master, slave = os.openpty()
    tty.setraw(slave)  # no echo / line editing before the app configures the port
    if os.path.lexists(device_path):
        os.remove(device_path)
    os.symlink(os.ttyname(slave), device_path)
    return master, slave  # keep slave open so the master never sees EOF


def modbus_crc(data: bytes) -> bytes:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, "little")


class S8:
    """Senseair S8 Modbus slave (address 0xFE)."""

    def __init__(self, device_path="/dev/ttyUSB0"):
        self.master, self._slave = open_pty(device_path)
        self.holding = {0x00: 0, 0x1F: 180}  # HR1 ack register, HR32 ABC period

    def respond(self, body: bytes):
        os.write(self.master, body + modbus_crc(body))

    def handle(self, frame: bytes):
        function = frame[1]
        register = int.from_bytes(frame[2:4], "big")
        value = int.from_bytes(frame[4:6], "big") if function != 0x44 else None
        if function == 0x44:  # legacy RAM read: CO2
            co2 = int(control().get("co2", 600)) & 0xFFFF
            self.respond(b"\xfe\x44\x02" + co2.to_bytes(2, "big"))
        elif function == 0x03:  # read holding register
            log_event("s8", "read_holding", register=register)
            self.respond(b"\xfe\x03\x02" + self.holding.get(register, 0).to_bytes(2, "big"))
        elif function == 0x06:  # write single holding register: echo the request
            log_event("s8", "write_holding", register=register, value=value)
            if register == 0x01 and value == 0x7C06:
                log_event("s8", "background_calibration")
                self.holding[0x00] |= 0x20
            else:
                self.holding[register] = value
            os.write(self.master, frame)
        else:
            log_event("s8", "unknown_function", function=function)

    def run(self):
        buffer = b""
        while True:
            buffer += os.read(self.master, 64)
            while len(buffer) >= 2:
                if buffer[0] != 0xFE:
                    buffer = buffer[1:]
                    continue
                length = 7 if buffer[1] == 0x44 else 8
                if len(buffer) < length:
                    break
                frame, buffer = buffer[:length], buffer[length:]
                if modbus_crc(frame[:-2]) != frame[-2:]:
                    log_event("s8", "bad_crc", frame=frame.hex())
                    continue
                self.handle(frame)


class PMS7003:
    """Plantower PMS7003 in active mode: pushes a 32-byte frame a few times a second."""

    def __init__(self, device_path="/dev/ttyAMA0"):
        self.master, self._slave = open_pty(device_path)

    @staticmethod
    def frame(pm1, pm25, pm10):
        words = [pm1, pm25, pm10, pm1, pm25, pm10, 500, 150, 30, 5, 1, 0, 0]  # cf1, std, counts, reserved
        body = b"\x42\x4d\x00\x1c" + b"".join(w.to_bytes(2, "big") for w in words)
        return body + sum(body).to_bytes(2, "big")

    def send_loop(self):
        while True:
            if control().get("pms", True):
                os.write(self.master, self.frame(5, 12, 20))
            time.sleep(0.3)

    def receive_loop(self):
        while True:
            data = os.read(self.master, 64)
            log_event("pms7003", "received", data=data.hex())


def start():
    os.makedirs(STATE_DIR, exist_ok=True)
    s8, pms = S8(), PMS7003()
    for target in (s8.run, pms.send_loop, pms.receive_loop):
        threading.Thread(target=target, daemon=True).start()
    log_event("harness", "started")
