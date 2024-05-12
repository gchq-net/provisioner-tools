import pyftdi.i2c
import pyftdi.eeprom


class provisioner:
    uri = ""  # URL to the FTDI chip used on the provisioner
    i2c = None  # pyftdi i2c object for provisioner

    def __init__(self, url: str = 'ftdi://ftdi:232h/1'):
        """Connects to and configures a provisioner"""
        self.url = url

        self.i2c = pyftdi.i2c.I2cController()
        self.i2c.configure(url)
        print(self.i2c.ftdi.ic_name)

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


# Print device info if run on its own
if __name__ == "__main__":
    device = provisioner()
    device.getInfo()
