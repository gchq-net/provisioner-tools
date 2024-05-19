import provisioner
import pyftdi
import questMarker


def hexString(data):
    """Converts data into a hex string for printing"""
    return ' '.join('{:02x}'.format(x) for x in data)


def checkCypto(quest_marker: questMarker.quest_marker):
    quest_marker.crypto.sendWake()
    print(hexString(quest_marker.crypto.get_serial_number()))
    if quest_marker.crypto.checkChipID():
        print("Serial is for ATSHA204A")


def checkEEPROM(quest_marker: questMarker.quest_marker):
    # check read of eeprom
    eeprom_current_data = quest_marker.eeprom.readAddr(0x0000, 10)

    # check fail to wrtite without WP assertion
    quest_marker.set_eeprom_wp(True)
    try:
        quest_marker.eeprom.writeAddr(0x0000, eeprom_current_data)
        print("Error can write without WP setting")
    except pyftdi.i2c.I2cNackError:
        pass

    quest_marker.set_eeprom_wp(False)
    quest_marker.eeprom.writeAddr(0x0000, eeprom_current_data)

    if (quest_marker.eeprom.readAddr(0x0000, 10) != eeprom_current_data):
        print("WARN EEPROM DATA NOT CONSISTENT")


if __name__ == "__main__":
    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    device.wait_for_detect()
    checkCypto(quest_marker)
    checkEEPROM(quest_marker)
    device.wait_for_no_detect()
