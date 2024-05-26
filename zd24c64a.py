import pyftdi.i2c


class zd24c64a:
    """Interface class for EEPROM IC"""
    i2c_port: pyftdi.i2c.I2cPort

    def __init__(self, i2c_port: pyftdi.i2c.I2cPort):
        self.i2c_port = i2c_port

    def writeAddr(self, address: int, data: "bytearray|list[int]"):
        output = [(address >> 8) & 0xFF, address & 0xFF]
        self.i2c_port.write(output + list(data))

    def readAddr(self, address: int, length: int):
        output = [(address >> 8) & 0xFF, address & 0xFF]
        self.i2c_port.write(output)
        return self.i2c_port.read(length)
