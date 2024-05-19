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
