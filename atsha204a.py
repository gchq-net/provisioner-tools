import enum
import pyftdi.i2c
import time


class atasha204A_command(enum.Enum):
    DERIVE_KEY = 0x1C
    DEV_REV = 0x30
    GEN_DIG = 0x15
    HMAC = 0x11
    CHECK_MAC = 0x28
    LOCK = 0x17
    MAC = 0x08
    NONCE = 0x16
    PAUSE = 0x01
    RANDOM = 0x1B
    READ = 0x02
    SHA = 0x47
    UPDATE_EXTRA = 0x20
    WRITE = 0x12


class atasha204A_zone(enum.Enum):
    CONFIG = 0x00
    OTP = 0x01
    DATA = 0x02


class atsha204A:
    i2c_port: pyftdi.i2c.I2cPort

    def __init__(self, i2c_port: pyftdi.i2c.I2cPort):
        self.i2c_port = i2c_port

#
# Helper commands
#

    def sendWake(self):
        """Sends a wake message to the ATSHA204A IC"""
        self.i2c_port.write(0x00)

    def sendCommand(self, oppcode: atasha204A_command, param1: int,
                    param2: int, data: "list[int]", response_length: int):
        """Sends a command to the Chip and recieves a response"""

        command = [
            0x03,  # command flag
            0x07 + len(data),  # count (includes fixed values)
            oppcode.value,  # command oppcode
            param1,  # paramter 1 value
            param2 & 0xff,  # paramater 2 value LSB
            param2 >> 8  # parameter 2 value MSB
        ]
        command += data  # add data to command

        crc = atsha204A.calculate_crc(command, 1, len(command) - 1)

        command += [
            crc & 0xFF,
            crc >> 8,
        ]

        self.i2c_port.write(command)
        time.sleep(0.1)
        # todo check incoming CRC
        return self.i2c_port.read(response_length)

    def calculate_crc(data: "bytearray|list[int]", offset: int, length: int):
        """Calculates the CRC for the ATSHA204A
        (poly 0805, start at 0x0000, reflect input,
        dont reflect output, no output exor)"""
        crc = 0x0000
        for i in range(0, length):
            d = data[offset + i]

            d = ((d & 0x55) << 1) | ((d & 0xAA) >> 1)
            d = ((d & 0x33) << 2) | ((d & 0xCC) >> 2)
            d = ((d & 0x0F) << 4) | ((d & 0xF0) >> 4)

            crc ^= d << 8
            for j in range(0, 8):
                if (crc & 0x8000) > 0:
                    crc = (crc << 1) ^ 0x8005
                else:
                    crc = crc << 1

        return crc & 0xFFFF

#
# ATSHA204A crypto commands
#

    def command_read(self, zone: atasha204A_zone, block: int, 
                     offset: int, four_byte=False):
        """Reads a block of memory from the IC"""

        param1 = zone.value
        if not four_byte:
            param1 += 0x80  # 32 byte read flag

        param2 = block << 3 + offset

        mem = self.sendCommand(
            atasha204A_command.READ,  # read command
            param1, param2, [],
            38)

        if four_byte:
            return mem[1:5]
        else:
            return mem[1:33]

#
# Top level commands
#
    def get_serial_number(self) -> bytearray:
        """Gets the serial number from the ATSHA204A"""
        mem = self.command_read(atasha204A_zone.CONFIG, 0, 0)

        serial_number = mem[0:4] + mem[8:13]
        return serial_number

    def checkChipID(self):
        """Checks if the Fixed bytes in the serial are correct"""
        serial = self.get_serial_number()

        if (serial[0] == 0x01 and serial[1] == 0x23 and serial[8] == 0xEE):
            return True
        else:
            return False
