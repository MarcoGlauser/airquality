import serial

from sensors.sensor import Sensor

s8_co2 = b'\xfe\x44\x00\x08\x02\x9F\x25'


class S8(Sensor):
    def read_data(self):
        output = None
        ser = serial.Serial('/dev/ttyUSB0', 9600, 8, 'N', 1, timeout=1)
        ser.write(s8_co2)
        while not output:
            output = ser.read(7)
        result = output[3] * 256 + output[4]
        return {
            'co2': result
        }
