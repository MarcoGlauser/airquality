import serial

from sensors.sensor import Sensor

s8_co2 = b"\xfe\x44\x00\x08\x02\x9F\x25"


class S8(Sensor):
    def read_data(self):
        output = None
        ser = serial.Serial("/dev/ttyUSB0", 9600, 8, "N", 1, timeout=1)
        ser.write(s8_co2)
        while not output:
            output = ser.read(7)
        result = output[3] * 256 + output[4]
        return {"carbon_dioxide": result}

    def home_assistant_auto_discovery(self) -> [str, dict]:
        return [
            (
                f"{self.home_assistant_prefix()}carbon_dioxide/config",
                self._home_assistant_discovery_helper("carbon_dioxide", "ppm"),
            )
        ]
