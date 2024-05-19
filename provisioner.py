import enum
import pyftdi.i2c
import pyftdi.eeprom


class provisioner_pinmap(enum.Enum):
    HEXPANSION_LS1 = 0x01 << 4  # ADBUS4
    HEXPANSION_LS2 = 0x01 << 5  # ADBUS5
    HEXPANSION_LS3 = 0x01 << 6  # ADBUS6
    HEXPANSION_LS4 = 0x01 << 7  # ADBUS7
    HEXPANSION_LS5 = 0x01 << 8  # ACBUS0
    HEXPANSION_HS1 = 0x01 << 9  # ACBUS1
    HEXPANSION_HS2 = 0x01 << 10  # ACBUS2
    HEXPANSION_HS3 = 0x01 << 11  # ACBUS3
    HEXPANSION_HS4 = 0x01 << 12  # ACBUS4
    STATUS_LED = 0x01 << 13  # ACBUS5
    HEXPANSION_DETECT = 0x01 << 14  # ACBUS6


class provisioner:
    """Class to control the Provisioner hardware and provide acces to its gpio control"""

    uri: str  # URL to the FTDI chip used on the provisioner
    i2c: pyftdi.i2c.I2cController  # pyftdi i2c object for provisioner
    gpio: pyftdi.i2c.I2cGpioPort

    def __init__(self, url: str = 'ftdi://ftdi:232h/1'):
        """Connects to and configures a provisioner"""
        self.url = url

        self.i2c = pyftdi.i2c.I2cController()
        self.i2c.configure(url)
        self.gpio = self.i2c.get_gpio()

        # Deactivate status LED
        self.set_gpio_mode(provisioner_pinmap.STATUS_LED, output=True)
        self.set_gpio_pin(provisioner_pinmap.STATUS_LED, False)

        # Set detect as input
        self.set_gpio_mode(provisioner_pinmap.HEXPANSION_DETECT, output=False)

    def getInfo(self):
        eeprom = pyftdi.eeprom.FtdiEeprom()
        eeprom.connect(self.i2c.ftdi)
        # print(eeprom.product)
        eeprom.dump_config()

    def get_i2c_port(self, address: int, shift=False) -> pyftdi.i2c.I2cPort:
        """Gets a pyftdi I2C port object for the given address"""
        if shift:
            return self.i2c.get_port(address >> 1)
        else:
            return self.i2c.get_port(address)

    def set_gpio_mode(self, pin: provisioner_pinmap, output: bool):
        current = self.gpio.direction

        if output:
            current |= pin.value
        else:
            current &= ~(pin.value)

        self.gpio.set_direction(pin.value, current)

    def set_gpio_pin(self, pin: provisioner_pinmap, state: bool):
        current = self.gpio.read(with_output=True)

        if state:
            current |= pin.value
        else:
            current &= ~(pin.value)

        self.gpio.write(current & self.gpio.direction)

    def get_gpio_pin(self, pin: provisioner_pinmap):
        current = self.gpio.read(with_output=True)
        if (current & pin.value):
            return True
        return False

    def wait_for_detect(self):
        while (True):
            if (self.get_gpio_pin(provisioner_pinmap.HEXPANSION_DETECT)):
                return True

    def wait_for_no_detect(self):
        while (True):
            if (not self.get_gpio_pin(provisioner_pinmap.HEXPANSION_DETECT)):
                return True


# Print device info if run on its own
if __name__ == "__main__":
    device = provisioner()
    device.getInfo()
