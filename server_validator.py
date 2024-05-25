import hashlib


def generate_diversified_key(
        chip_serial_number: "bytearray|list[int]",
        root_key: "bytearray|list[int]",
        target_slot: int,
        ) -> bytearray:
    """Geneates the diversified key for a given device"""
    serial_pad = [0x00] * (32 - 9)

    generation_hash_data = list(root_key)
    generation_hash_data += [0x1C, 0x04, target_slot & 0xFF, (target_slot >> 8) & 0xFF]
    generation_hash_data += [0xEE, 0x01, 0x23]
    generation_hash_data += [0x00] * 25
    generation_hash_data += list(chip_serial_number) + serial_pad

    diversified_key = hashlib.sha256(bytes(
        generation_hash_data
    )).digest()

    return diversified_key


def badge_response_calculation(
        atsha_serial: "bytearray|list[int]",
        atsha_random: "bytearray|list[int]",
        nonce: "bytearray|list[int]",
        master_key: "bytearray|list[int]",
        slot: int = 0x00,
        ) -> bytearray:
    """verifies a response from a badge"""

    # generate diversified key used on the badge
    marker_key = generate_diversified_key(atsha_serial, master_key, 0x00)

    import main

    print(main.hexString(marker_key))

    # generate tempkey after nonce command
    noncedata = list(atsha_random) + list(nonce) + [0x16, 0x00, 0x00]
    atsha_tempkey = hashlib.sha256(
        bytes(noncedata)
    ).digest()

    # generate expected result from chip
    otherdata = [0x08, 0x01, slot, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    # perform a local mac command
    macdata = list(marker_key) + list(atsha_tempkey)
    macdata += otherdata[0:4] + [0x00]*8 + otherdata[4:7] + [0xEE] + otherdata[7:11] + [0x01, 0x23] + otherdata[11:13]
    client_resp = hashlib.sha256(
        bytes(macdata)
    ).digest()

    return client_resp
