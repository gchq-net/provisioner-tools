import provisioner
import atsha204a


def hexString(data):
    """Converts data into a hex string for printing"""
    return ' '.join('{:02x}'.format(x) for x in data)


def checkCypto(provisioner: provisioner.provisioner):
    crypto = atsha204a.atsha204A(provisioner.get_i2c_port(0xC8, shift=True))
    crypto.sendWake()
    print(hexString(crypto.get_serial_number()))
    if crypto.checkChipID():
        print("Serial is for ATSHA204A")


if __name__ == "__main__":
    device = provisioner.provisioner()
    device.wait_for_detect()
    checkCypto(device)
    device.wait_for_no_detect()
