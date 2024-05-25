import hashlib
import utils


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
        badge_mac: "bytearray|list[int]",
        master_key: "bytearray|list[int]",
        slot: int = 0x00,
        ) -> bytearray:
    """verifies a response from a badge"""

    # generate diversified key used on the badge
    marker_key = generate_diversified_key(atsha_serial, master_key, 0x00)

    formatted_mac = bytearray("{:02X}-{:02X}-{:02X}-{:02X}-{:02X}-{:02X}".format(
        badge_mac[0], badge_mac[1], badge_mac[2],
        badge_mac[3], badge_mac[4], badge_mac[5]
        ), "ascii")

    challenge = list(formatted_mac) + [0x00] * 3

    # generate tempkey after nonce command
    noncedata = list(atsha_random) + list(challenge) + [0x16, 0x01, 0x00]
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


if __name__ == "__main__":
    # check against a set of data provided by a real badge
    import json

    badge_mac = [0xDC, 0x54, 0x75, 0xD8, 0x6E, 0x88]

    serial = b'\x01#]\xc2Q-\xb7a\xee'
    random = b'N\xab\x86\xb4\xfc\xe89`\\\xb5\xe0\x9f\xb8H`\xdbN_\xe3g\x81\x86\xff\x17\xfc\x88\xb0.\xea\xf4#\xcb'
    response = b'\x1a\x16\x03b$\x02\xd7\xdf\xe7\xb448\xc9\xa2~n\x82\x04\xa5\xefS+\x15\xafr\xd5Uo1\xc7\xa1a'

    print(utils.hexString(serial))

    with open("secrets.json") as file:
        raw_keys = json.load(file)
        keys = dict()
        for id in raw_keys:
            keys[bytearray.fromhex(id)[0]] = bytearray.fromhex(raw_keys[id])

    expected = badge_response_calculation(serial, random, badge_mac, keys[0])

    print(utils.hexString(response))
    print(utils.hexString(expected))
