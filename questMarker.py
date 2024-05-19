import provisioner
import atsha204a
import zd24c64a

PIN_STATUS_LED = provisioner.provisioner_pinmap.HEXPANSION_LS1
PIN_EEPROM_WP = provisioner.provisioner_pinmap.HEXPANSION_LS2


class quest_marker:
    """Wrapper for interfacing with a quest marker board"""

    _provisioner: provisioner.provisioner
    crypto: atsha204a.atsha204A
    eeprom: zd24c64a.zd24c64a

    def __init__(self, provisioner_device: provisioner.provisioner):
        self._provisioner = provisioner_device

        self.eeprom = zd24c64a.zd24c64a(
            self._provisioner.get_i2c_port(0x57))
        self.crypto = atsha204a.atsha204A(
            self._provisioner.get_i2c_port(0xC8, shift=True))

    def set_status_led(self, status: bool):
        self._provisioner.set_gpio_pin(PIN_STATUS_LED, not status)

    def set_eeprom_wp(self, protected: bool):
        if protected:
            self._provisioner.set_gpio_mode(PIN_EEPROM_WP, False)
        else:
            self._provisioner.set_gpio_mode(PIN_EEPROM_WP, True)
            self._provisioner.set_gpio_pin(PIN_EEPROM_WP, False)
