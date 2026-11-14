import os
import threading
from dataclasses import dataclass
from time import sleep

import serial

from sensors.sensor import Sensor, SensorError

s8_co2 = b"\xfe\x44\x00\x08\x02\x9F\x25"
s8_abc_status = b"\xfe\x03\x00\x1f\x00\x01\xa1\xc3"
s8_abc_enable = b"\xfe\x06\x00\x1f\x00\xb4\xac\x74"
S8_ABC_PERIOD_HOURS = 0xB4  # 180h, the value s8_abc_enable writes

s8_clear_hr1 = b"\xfe\x06\x00\x00\x00\x00\x9D\xC5"
s8_read_hr1  = b"\xfe\x03\x00\x00\x00\x01\x90\x05"
s8_start_calibration = b"\xFE\x06\x00\x01\x7c\x06\x6C\xC7"


@dataclass
class ModbusResponse:
    address: int
    function: int
    byte_count: int
    data: bytes
    crc: bytes
    message_without_crc: bytes

    def __init__(self, response: bytes):
        self.address = response[0]
        self.function = response[1]
        self.byte_count = response[2]
        self.data = response[3:-2]
        self.crc = response[-2:]
        self.message_without_crc = response[:-2]
        if self.crc != self.generate_crc():
            raise ValueError("CRC Mismatch")


    def data_as_int(self):
        return int.from_bytes(self.data, "big")

    def generate_crc(self):
        crc = 0xFFFF
        for byte in self.message_without_crc:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, "little")


class S8(Sensor):
    def __init__(self):
        super().__init__()
        self.serial = serial.Serial("/dev/ttyUSB0", 9600, 8, "N", 1, timeout=1)
        # set from the MQTT thread, handled in read_data so serial access stays on the main loop
        self.calibration_requested = threading.Event()

        self.ensure_abc_enabled()

    def ensure_abc_enabled(self):
        # Only write HR32 when it differs: rewriting it on every start may reset the ABC
        # history, and every write wears the sensor's EEPROM.
        abc_period = self.send_command(s8_abc_status, 7).data_as_int()
        if abc_period == S8_ABC_PERIOD_HOURS:
            print(f"S8 ABC already enabled ({abc_period}h)")
            return
        print(f"S8 ABC period is {abc_period}h, setting to {S8_ABC_PERIOD_HOURS}h")
        self.send_command(s8_abc_enable)

    def read_response(self, size) -> ModbusResponse:
        output = None
        while not output:
            output = self.serial.read(size)
        return ModbusResponse(output)

    def force_calibration(self):
        """Background calibration: tells the sensor the current air is 400 ppm."""
        self.send_command(s8_clear_hr1)
        calibration_ack = self.send_command(s8_start_calibration)
        print({"starting calibration": calibration_ack})
        sleep(4)
        calibration_result = self.send_command(s8_read_hr1)
        # bit 5 of HR1 is set by the sensor once background calibration is done
        if not calibration_result.data_as_int() & 0x20:
            raise SensorError(f"S8 calibration not acknowledged: {calibration_result}")
        print({"calibration finished": calibration_result})

    def send_command(self, command: bytes, expected_response_size:int = 100) -> ModbusResponse:
        self.serial.flush()
        self.serial.write(command)
        return self.read_response(expected_response_size)

    def read_data(self):
        if self.calibration_requested.is_set():
            self.calibration_requested.clear()
            try:
                self.force_calibration()
            except SensorError as e:
                # still publish the reading below, a failed calibration shouldn't hide it
                print(e)
        response = self.send_command(s8_co2,7)
        # the sensor reports a signed value: a drifted baseline shows up as negative ppm
        # (which used to be published as ~65000)
        co2 = int.from_bytes(response.data, "big", signed=True)
        if co2 < 0:
            print(f"S8 reported {co2} ppm, baseline is off - recalibrate in fresh air")
        return {"carbon_dioxide": co2}

    def home_assistant_auto_discovery(self) -> [str, dict]:
        return [
            (
                f"{self.home_assistant_prefix()}carbon_dioxide/config",
                self._home_assistant_discovery_helper("carbon_dioxide", "ppm"),
            ),
            (
                f"{os.getenv('MQTT_TOPIC_PREFIX', 'homeassistant')}/button/{type(self).__name__}/calibrate/config",
                {
                    "name": "Calibrate CO2 (fresh air)",
                    "command_topic": self.calibrate_command_topic(),
                    "unique_id": f"{type(self).__name__}_calibrate",
                    "icon": "mdi:window-open-variant",
                    "entity_category": "config",
                    # same identifier as the CO2 sensor, so the button shows up on that device
                    "device": {
                        "identifiers": [f"{type(self).__name__}_carbon_dioxide"],
                        "name": type(self).__name__,
                    },
                },
            ),
        ]

    def calibrate_command_topic(self) -> str:
        return f"{self.home_assistant_prefix()}/calibrate"

    def command_handlers(self) -> dict:
        def request_calibration(client, userdata, message):
            print("S8 calibration requested via MQTT")
            self.calibration_requested.set()

        return {self.calibrate_command_topic(): request_calibration}
