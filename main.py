import provisioner
import pyftdi
import atsha204a
import zd24c64a


def hexString(data):
    """Converts data into a hex string for printing"""
    return ' '.join('{:02x}'.format(x) for x in data)


def checkCypto(provisioner: provisioner.provisioner):
    crypto = atsha204a.atsha204A(provisioner.get_i2c_port(0xC8, shift=True))
    crypto.sendWake()
    print(hexString(crypto.get_serial_number()))
    if crypto.checkChipID():
        print("Serial is for ATSHA204A")


def checkEEPROM(device: provisioner.provisioner):
    eeprom = zd24c64a.zd24c64a(device.get_i2c_port(0x57))

    # check read of eeprom
    eeprom_current_data = eeprom.readAddr(0x0000, 10)

    # check fail to wrtite without WP assertion
    device.set_gpio_mode(provisioner.provisioner_pinmap.HEXPANSION_LS2, False)
    try:
        eeprom.writeAddr(0x0000, eeprom_current_data)
        print("Error can write without WP setting")
    except pyftdi.i2c.I2cNackError:
        pass

    device.set_gpio_mode(provisioner.provisioner_pinmap.HEXPANSION_LS2, True)
    device.set_gpio_pin(provisioner.provisioner_pinmap.HEXPANSION_LS2, False)
    eeprom.writeAddr(0x0000, eeprom_current_data)

    if (eeprom.readAddr(0x0000, 10) != eeprom_current_data):
        print("WARN EEPROM DATA NOT CONSISTENT")


if __name__ == "__main__":
    device = provisioner.provisioner()
    device.wait_for_detect()
    checkCypto(device)
    checkEEPROM(device)
    device.wait_for_no_detect()
