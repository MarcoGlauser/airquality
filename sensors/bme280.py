import bme280.const as oversampling
import smbus2

import bme280
from sensors.sensor import Sensor


class BME280(Sensor):
    def __init__(self):
        self.port = 1
        self.address = 0x76
        self.bus = smbus2.SMBus(self.port)
        self.calibration_params = bme280.load_calibration_params(self.bus, self.address)
        self.setup()

    def setup(self):
        mode = 0  # sleep
        self.bus.write_byte_data(self.address, 0xF2, oversampling.x1)  # ctrl_hum
        self.bus.write_byte_data(self.address, 0xF4, oversampling.x1 << 5 | oversampling.x1 << 2 | mode)  # ctrl

    def read_data(self):
        data = bme280.sample(self.bus, address=self.address, compensation_params=self.calibration_params)
        return {
            'temperature': data.temperature,
            'pressure': data.pressure,
            'humidity': data.humidity
        }