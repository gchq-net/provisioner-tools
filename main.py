import provisioner
import atsha204a


def checkCypto(provisioner: provisioner.provisioner):
    crypto = atsha204a.atsha204A(provisioner.get_i2c_port(0xC8, shift=True))
    crypto.sendWake()
    crypto.checkChipID()


if __name__ == "__main__":
    device = provisioner.provisioner()
    checkCypto(device)
