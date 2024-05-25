import provisioner
import atsha204a
import zd24c64a
import pyftdi


PIN_STATUS_LED = provisioner.provisioner_pinmap.HEXPANSION_LS1
PIN_EEPROM_WP = provisioner.provisioner_pinmap.HEXPANSION_LS2


class quest_marker:
    """Wrapper for interfacing with a quest marker board"""

    _provisioner: provisioner.provisioner
    crypto: atsha204a.atsha204A
    eeprom: zd24c64a.zd24c64a

    def __init__(self, provisioner_device: provisioner.provisioner):
        """Initialises a quest marker board based on the provisioner"""
        self._provisioner = provisioner_device

        self.eeprom = zd24c64a.zd24c64a(
            self._provisioner.get_i2c_port(0x57))
        self.crypto = atsha204a.atsha204A(
            self._provisioner.get_i2c_port(0xC8, shift=True))

    def set_status_led(self, status: bool):
        """Sets the Status LED on the board"""
        self._provisioner.set_gpio_pin(PIN_STATUS_LED, not status)

    def set_eeprom_wp(self, protected: bool):
        """Sets the wprom write protect status"""
        if protected:
            self._provisioner.set_gpio_mode(PIN_EEPROM_WP, False)
        else:
            self._provisioner.set_gpio_mode(PIN_EEPROM_WP, True)
            self._provisioner.set_gpio_pin(PIN_EEPROM_WP, False)

# higher level configuration funcions

    def basic_self_test(self, eeprom_write=False):
        """Performs a basic automated self test on the board"""

        results = dict()

        # Check the Crypto processor
        try:
            self.crypto.checkChipID()
            results["crypto"] = {"passed": True}
        except Exception as e:
            results["crypto"] = {"passed": False, "message": str(e)}

        # Check the EEPROM
        eeprom_current_data = list()
        try:
            eeprom_current_data = self.eeprom.readAddr(0x0000, 10)
            results["eeprom_read"] = {"passed": True}
        except Exception as e:
            results["eeprom_read"] = {"passed": False, "message": str(e)}

        # check fail to wrtite without WP assertion
        self.set_eeprom_wp(True)
        try:
            self.eeprom.writeAddr(0x0000, eeprom_current_data)
            results["eeprom_write_protect"] = {
                "passed": False,
                "message": "Write succedded WP not active"}
        except pyftdi.i2c.I2cNackError:
            results["eeprom_write_protect"] = {"passed": True}
        except Exception as e:
            results["eeprom_write_protect"] = {
                "passed": False,
                "message": str(e)}

        if (eeprom_write):
            self.set_eeprom_wp(False)
            try:
                self.eeprom.writeAddr(0x0000, eeprom_current_data)
                results["eeprom_write"] = {"passed": True}
            except Exception as e:
                results["eeprom_write"] = {"passed": False, "message": str(e)}

        self.set_eeprom_wp(True)

        try:
            new_data = self.eeprom.readAddr(0x0000, 10)
            if (new_data != eeprom_current_data):
                results["eeprom_consistent"] = {
                    "passed": False,
                    "message": "EEPROM dosesnt match previous data"}
            else:
                results["eeprom_consistent"] = {"passed": True}
        except Exception as e:
            results["eeprom_consistent"] = {"passed": False, "message": str(e)}

        tests_passed = True
        for item in results:
            if (results[item].get("passed", False) is False):
                tests_passed = False

        return (tests_passed, results)

    def write_crypto_config(self):
        """Configures the data zone for the atsha204A"""

        # configure the ATSHA204A config zone

        config_zone_data = [
            0xC8,  # I2C Address (default)
            0x00,  # CheckMacConfig (use rand in nonces for read/write)
            0xAA,  # OTPmode (locked)
            0x00,  # SelectorMode
            0x80, 0x4F,  # Slot 0 (secret, enc write by slot F)
            0x80, 0x4F,  # Slot 1 (secret, enc write by slot F)
            0x80, 0x4E,  # Slot 2 (secret, enc write by slot E)
            0x80, 0x4E,  # Slot 3 (secret, enc write by slot E)
            0x00, 0x4E,  # Slot 4 (public, enc write by slot E)
            0x00, 0x4E,  # Slot 5 (public, enc write by slot E)
            0x00, 0x4E,  # Slot 6 (public, enc write by slot E)
            0x00, 0x4E,  # Slot 7 (public, enc write by slot E)
            0xC9, 0x4F,  # slot 8 (secret, enc read by slot 9, enc write by slot F)
            0x80, 0x4F,  # Slot 9 (secret, enc write by slot F)
            0xCB, 0x4E,  # slot A (secret, enc read by slot B, enc write by slot E)
            0x80, 0x4E,  # Slot B (secret, enc write by slot E)
            0xCD, 0x4E,  # slot C (secret, enc read by slot D, enc write by slot E)
            0x80, 0x4E,  # Slot D (secret, enc write by slot E)
            0x90, 0x4F,  # slot E (secret, check only, enc write by slot F)
            0x90, 0x80,   # slot F (secret, check only, never write)
            0xFF,  # UseFlag 0
            0x00,  # UpdateCount 0
            0xFF,  # UseFlag 1
            0x00,  # UpdateCount 1
            0xFF,  # UseFlag 2
            0x00,  # UpdateCount 2
            0xFF,  # UseFlag 3
            0x00,  # UpdateCount 3
            0xFF,  # UseFlag 4
            0x00,  # UpdateCount 4
            0xFF,  # UseFlag 5
            0x00,  # UpdateCount 5
            0xFF,  # UseFlag 6
            0x00,  # UpdateCount 6
            0xFF,  # UseFlag 7
            0x00,  # UpdateCount 7
            0xFF, 0xFF, 0xFF, 0xFF,  # LastKeyUse 0-3
            0xFF, 0xFF, 0xFF, 0xFF,  # LastKeyUse 4-7
            0xFF, 0xFF, 0xFF, 0xFF,  # LastKeyUse 8-11
            0xFF, 0xFF, 0xFF, 0xFF,  # LastKeyUse 12-15
        ]

        for x in range(17):

            addr = x+4
            block = addr >> 3
            offset = addr & 0x07

            print(addr, block, offset)
            self.crypto.command_write(atsha204a.atasha204A_zone.CONFIG, block, offset, config_zone_data[x*4:x*4+4], four_byte=True)

        # lock the config zone TODO can replace with just reading start and end

        config = list()
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 0, 0))
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 1, 0))
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 2, 0, four_byte=True))
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 2, 1, four_byte=True))
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 2, 2, four_byte=True))
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 2, 3, four_byte=True))
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 2, 4, four_byte=True))
        config += list(self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 2, 5, four_byte=True))

        # config_low = self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 0, 0)
        # config_end = self.crypto.command_read(atsha204a.atasha204A_zone.CONFIG, 2, 5, four_byte=True)

        targetconfig = config[0:16] + config_zone_data + config[84:88]

        config_crc = atsha204a.atsha204A.calculate_crc(targetconfig, 0, 88)

        self.crypto.command_lock(False, config_crc)

    def write_crypto_data(self, serial, keys):
        """writes the data to the atsha204A"""

        # generate OTP data

        otp_low = bytes("SN:{:04X} HW:{} CONF:{} ".format(serial, "1.0", "1.0"), "ascii")
        otp_high = bytes("GCHQ.NET HEXPANSION", "ascii")

        otp_low = (otp_low + b'\x00'*32)[0:32]
        otp_high = (otp_high + b'\x00'*32)[0:32]

        # program data and otp

        for x in range(16):
            self.crypto.command_write(atsha204a.atasha204A_zone.DATA, x, 0, keys[x])
        self.crypto.command_write(atsha204a.atasha204A_zone.OTP, 0, 0, otp_low)
        self.crypto.command_write(atsha204a.atasha204A_zone.OTP, 1, 0, otp_high)

        # lock data

        crcstream = list()
        for x in range(16):
            crcstream += list(keys[x])
        crcstream += list(otp_low)
        crcstream += list(otp_high)

        print(len(crcstream))

        data_crc = atsha204a.atsha204A.calculate_crc(crcstream, 0, len(crcstream))

        self.crypto.command_lock(True, data_crc)

        # validate data

        for x in range(16):
            print(x)
            self.crypto.check_key(x, keys[x])

        print(list(self.crypto.command_read(atsha204a.atasha204A_zone.OTP, 0, 0)) == list(otp_low))
        print(list(self.crypto.command_read(atsha204a.atasha204A_zone.OTP, 1, 0)) == list(otp_high))

    def provision(self):
        """Performs first time setup for the hexpansion"""

        import json

        with open("secrets.json") as file:
            raw_keys = json.load(file)
            keys = dict()
            for id in raw_keys:
                keys[bytearray.fromhex(id)[0]] = bytearray.fromhex(raw_keys[id])

        # print(keys)

        self.write_crypto_config()
    def perform_challenge(
            self,
            badge_mac: "bytearray|list[int]",
            slot: int = 0x00
            ) -> "tuple[bytearray, bytearray]":
        """performs a challenge against the badge"""

        challenge = [0x00] * 20

        # perform a nonce command
        random = self.crypto.command_nonce(0x00, challenge)

        # perform the mac command
        response = self.crypto.command_mac(slot, [], use_tempkey_end=True)

        return (random, response)
