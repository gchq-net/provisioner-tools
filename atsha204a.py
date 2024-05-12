import pyftdi.i2c
import time


class atsha204A:
    i2c_port = None

    def __init__(self, i2c_port: pyftdi.i2c.I2cPort):
        self.i2c_port = i2c_port

#
# Helper commands
#

    def sendWake(self):
        """Sends a wake message to the ATSHA204A IC"""
        self.i2c_port.write(0x00)

    def sendCommand(self, oppcode: int, param1: int, param2: int,
                    data: "list[int]", response_length: int):
        """Sends a command to the Chip and recieves a response"""

        command = [
            0x03,  # command flag
            0x07 + len(data),  # count (includes fixed values)
            oppcode,  # command oppcode
            param1,  # paramter 1 value
            param2 >> 8,  # paramater 2 value MSB
            param2 & 0xff  # parameter 2 value LSB
        ]
        command += data  # add data to command

        crc = atsha204A.crc16(command, 1, len(command) - 1)

        command += [
            crc & 0xFF,
            crc >> 8,
        ]

        self.i2c_port.write(command)
        time.sleep(0.1)
        # todo check incoming CRC
        return self.i2c_port.read(response_length)

    def crc16(data: bytearray, offset: int, length: int):
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
# Top level commands
#

    def checkChipID(self):
        # read intial memory block
        mem = self.sendCommand(
            0x02,  # read command
            0x80,  # 32 bytes from data block
            0x0000,  # read fist four bytes
            [],  # no data
            38)

        print(''.join('{:02x}'.format(x) for x in mem))

        if (mem[1] == 0x01 and mem[2] == 0x23 and mem[13] == 0xEE):
            return True
        else:
            return False
