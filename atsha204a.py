import enum
import hashlib
import pyftdi.i2c
import time
import utils


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

        # print("Sent command" + ' '.join('{:02x}'.format(x) for x in command))

        self.i2c_port.write(command)

        response = None
        for x in range(10):
            time.sleep(0.02)
            try:
                # todo check incoming CRC
                # print("reading")
                response = self.i2c_port.read(response_length)
                break
            except pyftdi.i2c.I2cNackError:
                # print("read error")
                pass
        if response is None:
            raise Exception("No response from chip")

        # print("Response" + ' '.join('{:02x}'.format(x) for x in response))

        if (response[0] == 0xFF):
            raise IOError("chip returned no data")

        resp_crc = atsha204A.calculate_crc(response, 0, response[0]-2)

        if ((resp_crc & 0xFF) != response[response[0]-2] or (resp_crc >> 8 & 0xFF) != response[response[0]-1]):
            raise IOError("chip response CRC mismatch {} {} != {} {}".format(
                hex(resp_crc & 0xFF), hex(resp_crc >> 8 & 0xFF),
                hex(response[response[0]-2]), hex(response[response[0]-1])
            ))

        if (response[0] == 0x04 and response[1] != 0x00):
            raise RuntimeError("Chip returned an error {}".format(hex(response[1])))

        # time.sleep(0.5)
        return response

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

    def command_checkmac(self,
                         slot: int,
                         client_chal: "bytearray|list[int]",
                         client_resp: "bytearray|list[int]",
                         other_Data: "bytearray|list[int]",
                         use_client_chal: bool = True,
                         use_slot: bool = True,
                         tempkey_src: bool = False,
                         use_otp: bool = False,
                         ):
        """Performs a checkmac command on the chip"""

        param1 = 0x00
        if not use_client_chal:
            param1 |= 0x01
        if not use_slot:
            param1 |= 0x02
        if tempkey_src:
            param1 |= 0x04
        if use_otp:
            param1 |= 0x20

        param2 = slot

        data = list(client_chal) + list(client_resp) + list(other_Data)

        mem = self.sendCommand(
            atasha204A_command.CHECK_MAC,  # read command
            param1, param2, data,
            38)

        return mem[1]

    def command_gendig(self,
                       zone: atasha204A_zone,
                       slot: int,
                       data=[]):
        """Performs a gendig command on the chip"""

        param1 = zone.value

        param2 = slot

        mem = self.sendCommand(
            atasha204A_command.GEN_DIG,  # read command
            param1, param2, data,
            38)

        return mem[1]

    def command_lock(self, lock_data, crc=None, skip_crc=False):

        param1 = 0x00
        if lock_data:
            param1 |= 0x01
        if skip_crc:
            param1 |= 0x01 << 7

        param2 = crc

        mem = self.sendCommand(
            atasha204A_command.LOCK,  # read command
            param1, param2, [],
            38)

        return mem[1]

    def command_mac(self,
                    slot_id: int,
                    challenge: bytearray,
                    include_sn: bool = False,
                    include_otp_low: bool = False,
                    include_otp_high: bool = False,
                    tempkey_srcflag: bool = False,
                    use_tempkey_start: bool = False,
                    use_tempkey_end: bool = False,
                    ) -> bytearray:
        """Performs a sha mac calculation"""

        param1 = 0x00
        if include_sn:
            param1 |= 0x40
        if include_otp_low:
            param1 |= 0x20
        if include_otp_high:
            param1 |= 0x10
        if tempkey_srcflag:
            param1 |= 0x04
        if use_tempkey_start:
            param1 |= 0x02
        if use_tempkey_end:
            param1 |= 0x01

        param2 = slot_id

        response = self.sendCommand(
            atasha204A_command.MAC,  # read command
            param1, param2, challenge,
            38)

        return response[1:33]

    def command_nonce(self, nonceMode, input=[]):
        """Generates a nonce on the chip"""

        param1 = nonceMode

        param2 = 0x0000

        mem = self.sendCommand(
            atasha204A_command.NONCE,  # read command
            param1, param2, input,
            38)

        if (nonceMode == 0x03):
            return mem[1]
        else:
            return mem[1:33]

    def command_read(self, zone: atasha204A_zone, block: int,
                     offset: int, four_byte=False):
        """Reads a block of memory from the IC"""

        param1 = zone.value
        if not four_byte:
            param1 += 0x80  # 32 byte read flag

        param2 = (block << 3) + offset

        mem = self.sendCommand(
            atasha204A_command.READ,  # read command
            param1, param2, [],
            38)

        if four_byte:
            return mem[1:5]
        else:
            return mem[1:33]

    def command_write(
            self,
            zone: atasha204A_zone,
            block: int,
            offset: int,
            data: "bytearray|list[int]",
            mac: "bytearray|list[int]|None" = None,
            four_byte: bool = False,
            encrypted: bool = False):
        pass
        """Writes a block of memory to the IC"""

        param1 = zone.value
        if encrypted:
            param1 |= 1 << 6  # encrypted write flag
        if not four_byte:
            param1 += 1 << 7  # 32 byte read flag

        param2 = (block << 3) + offset

        command_data = list(data)
        if (mac is not None):
            command_data += list(mac)

        mem = self.sendCommand(
            atasha204A_command.WRITE,  # read command
            param1, param2, command_data,
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

    def read_config(self):
        """Reads the entire configuration zone"""

        config = list()
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 0, 0))
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 1, 0))
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 2, 0, four_byte=True))
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 2, 1, four_byte=True))
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 2, 2, four_byte=True))
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 2, 3, four_byte=True))
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 2, 4, four_byte=True))
        config += list(utils.auto_retry(self.command_read, 5, atasha204A_zone.CONFIG, 2, 5, four_byte=True))

        return (config)

    def encrypted_read(
            self,
            readslot: int,
            readkey_slot: int,
            readkey: "bytearray|list[int]",
            nonce_type: int = 0x00,
            nonce: "bytearray|list[int]" = [0x00]*20):
        """Performs a sequence of commands to perform an encrtpted read"""

        # get the device serial number //TODO can replace with fixed data
        serial = self.get_serial_number()

        # populate tempkey with a nonce with a provided nonce type
        random = self.command_nonce(nonce_type, nonce)

        # create a gendig command and provide the standard data for checkonly keys
        self.command_gendig(atasha204A_zone.DATA, readkey_slot,
                            [0x15, 0x02, readkey_slot, 0x00])

        # calculate the contents of the atsha204a tempkey
        chip_nonce = None
        if nonce_type != 0x03:
            noncedata = list(random) + list(nonce) + [0x16, 0x00, 0x00]

            chip_nonce = hashlib.sha256(
                bytes(noncedata)
            ).digest()
        else:
            chip_nonce = nonce

        # calculate the result of the gendig command to get the tempkey value used as a session key
        hashdata = list(readkey)
        hashdata += [0x15, 0x02, readkey_slot, 0x00, serial[8], serial[0], serial[1]]
        hashdata += [0x00]*25 + list(chip_nonce)

        session_key = hashlib.sha256(
            bytes(hashdata)
        ).digest()

        # read the data from the chip
        data = self.command_read(atasha204A_zone.DATA, readslot, 0)

        # exor the data with the session key to get the value
        xored = bytes(a ^ b for a, b in zip(data, session_key))

        return xored

    def encrypted_write(
            self,
            write_slot: int,
            data: "bytearray|list[int]",
            writekey_slot: int,
            writekey: "bytearray|list[int]",
            nonce_type: int = 0x00,
            nonce: "bytearray|list[int]" = [0x00]*20):
        """Performs a sequence of commands to perform an encrypted write"""

        # get the device serial number //TODO can replace with fixed data
        serial = self.get_serial_number()

        # populate tempkey with a nonce with a provided nonce type
        random = self.command_nonce(nonce_type, nonce)

        # create a gendig command and provide the standard data for checkonly keys
        self.command_gendig(atasha204A_zone.DATA, writekey_slot,
                            [0x15, 0x02, writekey_slot, 0x00])

        # calculate the contents of the atsha204a tempkey
        chip_nonce = None
        if nonce_type != 0x03:
            noncedata = list(random) + list(nonce) + [0x16, 0x00, 0x00]

            chip_nonce = hashlib.sha256(
                bytes(noncedata)
            ).digest()
        else:
            chip_nonce = nonce

        # calculate the result of the gendig command to get the tempkey value used as a session key
        hashdata = list(writekey)
        hashdata += [0x15, 0x02, writekey_slot, 0x00, serial[8], serial[0], serial[1]]
        hashdata += [0x00]*25 + list(chip_nonce)

        session_key = hashlib.sha256(
            bytes(hashdata)
        ).digest()

        # xor the data with the session_key
        xored = bytes(a ^ b for a, b in zip(data, session_key))

        # calculate the mac value
        write_addr = write_slot << 3
        mac = hashlib.sha256(bytes(
            list(session_key) +
            [0x12, 0x82, write_addr & 0xFF, (write_slot >> 8) & 0xFF, serial[8], serial[0], serial[1]] +
            [0x00]*25 + list(data)
        )).digest()

        # perform the write command
        self.command_write(
            atasha204A_zone.DATA,
            write_slot, 0,
            xored,
            mac,
            encrypted=False  # it is actualy encrypted but encryption is ignored after zones are locked
        )

    def generate_diversified_key(
            self,
            root_key: "bytearray|list[int]",
            target_slot: int,
            ):
        """
        Geneates a diversified key for the device
        Uses implementation in Atmel-8841A-CryptoAuth-ATSHA204-Unique-Keys-ApplicationNote_042013
        """
        serial = self.get_serial_number()

        serial_pad = [0x00] * (32 - 9)

        generation_hash_data = list(root_key)
        generation_hash_data += [0x1C, 0x04, target_slot & 0xFF, (target_slot >> 8) & 0xFF]
        generation_hash_data += [0xEE, 0x01, 0x23]
        generation_hash_data += [0x00] * 25
        generation_hash_data += list(serial) + list(serial_pad)

        diversified_key = hashlib.sha256(bytes(
            generation_hash_data
        )).digest()

        return diversified_key

    def check_key(self, slot: int, key: "bytearray|list[int]"):
        """Checks a key matches the expected value"""

        client_chal = [0x00]*32

        otherdata = [0x08, 0x00, slot, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        # perform a local mac command
        macdata = list(key) + list(client_chal)
        macdata += otherdata[0:4] + [0x00]*8 + otherdata[4:7]
        macdata += [0xEE] + otherdata[7:11] + [0x01, 0x23] + otherdata[11:13]
        client_resp = hashlib.sha256(
            bytes(macdata)
        ).digest()

        self.command_checkmac(slot, client_chal, client_resp, otherdata)
