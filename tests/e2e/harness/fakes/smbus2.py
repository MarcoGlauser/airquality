"""Stand-in for smbus2 inside the e2e container.

I2C ioctls can't be emulated in a container, so this serves register maps for the
BME280 and LTR559 instead. The real bme280 / ltr559 / i2cdevice libraries run on top
of it, so their register reads and math are still exercised.
"""

import threading

_lock = threading.Lock()


def _le16(value):
    value &= 0xFFFF
    return [value & 0xFF, value >> 8]


def _bme280_registers():
    regs = bytearray(256)
    regs[0xD0] = 0x60  # chip id
    # calibration + raw values from the Bosch BME280 datasheet example:
    # adc_T=519888 -> 25.08 °C, adc_P=415148 -> 1006.53 hPa
    calibration = {
        0x88: 27504, 0x8A: 26435, 0x8C: -1000,  # T1..T3
        0x8E: 36477, 0x90: -10685, 0x92: 3024, 0x94: 2855, 0x96: 140,  # P1..P5
        0x98: -7, 0x9A: 15500, 0x9C: -14600, 0x9E: 6000,  # P6..P9
        0xE1: 362,  # H2
    }
    for reg, value in calibration.items():
        regs[reg:reg + 2] = bytes(_le16(value))
    regs[0xA1] = 75  # H1
    regs[0xE3] = 0  # H3
    regs[0xE4], regs[0xE5], regs[0xE6] = 0x14, 0x04, 0x00  # H4=324, H5=0
    regs[0xE7] = 30  # H6
    adc_p, adc_t, adc_h = 415148, 519888, 30000
    regs[0xF7:0xFF] = bytes([
        (adc_p >> 12) & 0xFF, (adc_p >> 4) & 0xFF, (adc_p << 4) & 0xF0,
        (adc_t >> 12) & 0xFF, (adc_t >> 4) & 0xFF, (adc_t << 4) & 0xF0,
        adc_h >> 8, adc_h & 0xFF,
    ])
    return regs


def _ltr559_registers():
    regs = bytearray(256)
    regs[0x86] = 0x92  # part number 0x09, revision 0x02
    regs[0x87] = 0x05  # manufacturer id
    ch1, ch0 = 200, 1000  # -> 997.74 lux with the driver's default gain/integration time
    regs[0x88:0x8C] = bytes(_le16(ch1) + _le16(ch0))
    regs[0x8C] = 0x04  # status: new ALS data available
    return regs


def _ltr559_on_write(regs, reg):
    if reg == 0x80:
        regs[0x80] &= ~0x02  # software reset completes immediately


DEVICES = {
    0x76: (_bme280_registers(), None),
    0x23: (_ltr559_registers(), _ltr559_on_write),
}


def _device(address):
    if address not in DEVICES:
        raise OSError(121, "Remote I/O error")  # what a missing device looks like on a real bus
    return DEVICES[address]


class SMBus:
    def __init__(self, bus=None, force=False):
        self.bus = bus

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def read_i2c_block_data(self, i2c_addr, register, length, force=None):
        regs, _ = _device(i2c_addr)
        with _lock:
            return list(regs[register:register + length])

    def write_i2c_block_data(self, i2c_addr, register, data, force=None):
        regs, on_write = _device(i2c_addr)
        with _lock:
            regs[register:register + len(data)] = bytes(data)
            if on_write:
                on_write(regs, register)

    def read_byte_data(self, i2c_addr, register, force=None):
        return self.read_i2c_block_data(i2c_addr, register, 1)[0]

    def read_word_data(self, i2c_addr, register, force=None):
        low, high = self.read_i2c_block_data(i2c_addr, register, 2)
        return low | high << 8

    def write_byte_data(self, i2c_addr, register, value, force=None):
        self.write_i2c_block_data(i2c_addr, register, [value])
