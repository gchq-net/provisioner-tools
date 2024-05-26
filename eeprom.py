import utils


FS_OFFSET = 32
FS_PAGE_SZE = 32
FS_TOTAL = 1024*8
VID = 0xF055
PID = 0x4247

LITTLEFS_BLOCK_SIZE = 512
LITTLEFS_BLOCK_COUNT = int((FS_TOTAL-32)/LITTLEFS_BLOCK_SIZE)


def generate_header_data(serial: int):
    """Generates the eeprom data header"""
    header = list()
    header += list(b'THEX')  # magic bytes
    header += list(b'2024')  # header version
    header += FS_OFFSET.to_bytes(2, 'little')
    header += FS_PAGE_SZE.to_bytes(2, 'little')
    header += FS_TOTAL.to_bytes(4, 'little')
    header += VID.to_bytes(2, 'little')
    header += PID.to_bytes(2, 'little')
    header += serial.to_bytes(2, 'little')  # padding
    header += list(b'GCHQ.NET') + [0x00]

    checksum = 0x55
    for byte in header[1:]:
        checksum ^= byte

    header += [checksum]

    return header


def check_littlefs_dump_against_file(data):

    with open("littlefs_blob", "r") as output:
        fs_dump = bytearray.fromhex(output.read())
        if list(fs_dump) == list(data):
            return True
        else:
            return False


def get_littlefs_image():
    with open("littlefs_blob", "r") as output:
        fs_dump = bytearray.fromhex(output.read())

    return fs_dump


if __name__ == "__main__":
    print(utils.hexString(generate_header_data(0x0000)))
