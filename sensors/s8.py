from dataclasses import dataclass

import serial

from sensors.sensor import Sensor

s8_co2 = b"\xfe\x44\x00\x08\x02\x9F\x25"
s8_abc_status = b"\xfe\x03\x00\x1f\x00\x01\xa1\xc3"
s8_abc_enable = b"\xfe\x06\x00\x1f\x00\xb4\xac\x74"


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

        print(f"Address: {self.address}")
        print(f"Function: {self.function}")
        print(f"Byte Count: {self.byte_count}")
        print(f"Data: {self.data}")
        print(f"CRC: {self.crc}")
        print(f"Generated CRC: {self.generate_crc()}")
        print(f"Data as int: {self.data_as_int()}")


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

        abc_status = self.send_command(s8_abc_enable, 8)
        print(f"ABC Status: {abc_status.data_as_int()}")

    def read_response(self, size) -> ModbusResponse:
        output = None
        while not output:
            output = self.serial.read(size)
        return ModbusResponse(output)

    def send_command(self, command: bytes, expected_response_size:int) -> ModbusResponse:
        self.serial.flush()
        self.serial.write(command)
        return self.read_response(expected_response_size)

    def read_data(self):
        response = self.send_command(s8_co2, 7)
        print({"carbon_dioxide": response.data_as_int()})
        return {"carbon_dioxide": response.data_as_int()}

    def home_assistant_auto_discovery(self) -> [str, dict]:
        return [
            (
                f"{self.home_assistant_prefix()}carbon_dioxide/config",
                self._home_assistant_discovery_helper("carbon_dioxide", "ppm"),
            )
        ]
