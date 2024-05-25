import click
import json
import provisioner
import questMarker
import server_validator


def hexString(data):
    """Converts data into a hex string for printing"""
    return ' '.join('{:02x}'.format(x) for x in data)


factoryData = {
    0x00: bytearray.fromhex(
        "00 00 A1 AC 57 FF 40 4E 45 D4 04 01 BD 0E D3 C6 73 D3 B7 B8 2D 85 D9 F3 13 B5 5E DA 3D 94 00 00"),
    0x01: bytearray.fromhex(
        "11 11 23 B6 CC 53 B7 B9 E9 BB 51 FD 2F 74 CD 0E 91 D9 7F EB 84 7B 98 09 F4 CD 93 6A B6 48 11 11"),
    0x02: bytearray.fromhex(
        "22 22 C1 7C 1C 4D 56 89 AA 00 43 E3 9C FB 6B 0B 68 49 E3 2C 24 A3 1B 06 34 49 1E 90 6B 62 22 22"),
    0x03: bytearray.fromhex(
        "33 33 33 61 4A 17 9A 23 6C 7F E4 BE 2F 13 20 67 90 3D B5 1C 72 E0 C9 31 29 6D F4 5A 3E 44 33 33"),
    0x04: bytearray.fromhex(
        "44 44 91 18 68 3D B8 D3 F8 57 0C 74 2E DA DA 52 88 87 30 A5 09 18 54 56 C9 A1 72 38 CF 3C 44 44"),
    0x05: bytearray.fromhex(
        "55 55 86 F2 B3 20 98 A6 E1 E6 33 7A 52 01 03 6A 0D B5 04 02 02 1C 55 B2 57 DF 0C 73 5F 05 55 55"),
    0x06: bytearray.fromhex(
        "66 66 D0 45 3A C2 25 57 F6 D4 6B 7D DF 96 89 DA 2C BC D9 C3 5A D5 9A 42 DE 30 32 CD 25 FC 66 66"),
    0x07: bytearray.fromhex(
        "77 77 2F 4A 9C C0 5E 45 99 BD 26 96 DD 49 F8 A5 06 C8 B6 39 CD 3D A8 4C C6 D1 3C 32 CA 0F 77 77"),
    0x08: bytearray.fromhex(
        "88 88 C6 2A FE 1F 82 D4 E0 85 85 34 4D 77 B8 9D EC 36 F2 06 27 E4 F0 CF 03 0E 27 B8 EE E3 88 88"),
    0x09: bytearray.fromhex(
        "99 99 4E 6D 4A F5 92 30 6B D2 D5 27 7D 77 B3 95 E3 C3 50 8C DA E0 98 1F 9D 28 17 98 8D F4 99 99"),
    0x0A: bytearray.fromhex(
        "AA AA 15 A2 55 0B D2 EA 9A F2 96 46 15 69 11 12 96 12 F6 F7 29 FD 50 7C 9A A2 67 92 A1 44 AA AA"),
    0x0B: bytearray.fromhex(
        "BB BB 24 DB 78 A8 70 64 A1 F0 8D C9 17 96 60 0A FF 62 D4 C4 4C 3E 10 20 2A AA 8F EC B6 8A BB BB"),
    0x0C: bytearray.fromhex(
        "CC CC C6 17 1A 52 45 AC D2 92 46 28 90 62 4C A5 66 2B 22 BB D1 95 DA 2A 9E 49 B8 08 85 0D CC CC"),
    0x0D: bytearray.fromhex(
        "DD DD BF AC 11 70 55 9C C9 B6 28 0F 92 95 DF 30 0D EA 22 A0 65 4E 21 C9 CE 74 10 5A 65 D2 DD DD"),
    0x0E: bytearray.fromhex(
        "EE EE 08 55 77 BD A7 B8 A7 AF 58 D1 8B 92 F0 DF 79 AD 05 5E 42 82 E9 42 1E D1 3D 7B BD 2E EE EE"),
    0x0F: bytearray.fromhex(
        "FF FF 68 B7 B8 01 BE 66 2C EC 74 68 0F E4 7D C1 C6 72 54 3A E5 BE DA 2E 91 9A E5 0D 32 A1 FF FF")
}


def send_basic_challenge(quest_marker: questMarker.quest_marker, slot):
    for x in range(10):
        try:
            response = quest_marker.crypto.command_mac(
                slot,
                bytearray([0x00]*32)
            )
            break
        except RuntimeError as e:
            raise e
        except Exception:
            pass
    return (response)


def read_public_var(quest_marker: questMarker.quest_marker, slot):

    for x in range(10):
        try:
            response = quest_marker.crypto.command_read(
                questMarker.atsha204a.atasha204A_zone.DATA,
                slot,
                0,
                False
            )
            break
        except Exception:
            pass
    return (response)


def encrypted_write(quest_marker: questMarker.quest_marker, slot, data, writekey_slot):

    writekey = factoryData[writekey_slot]

    for x in range(10):
        try:
            quest_marker.crypto.encrypted_write(
                slot, data,
                writekey_slot, writekey
            )
            break
        # except RuntimeError as e:
        #     raise e
        except Exception as e:
            if x == 9:
                raise e

    print("Wrote data to slot {} with key {}".format(hex(slot), hex(writekey_slot)))

    return


def encrypted_read(quest_marker: questMarker.quest_marker, slot):

    readkey = factoryData[slot+1]

    for x in range(10):
        try:
            data = quest_marker.crypto.encrypted_read(slot, slot+1, readkey)
            break
        except Exception:
            pass

    return (data)


def crypto_config_test(quest_maker: questMarker.quest_marker):
    """Performs checks on the config of the crypto IC"""

    # check OTP read
    otp_data_low = quest_marker.crypto.command_read(questMarker.atsha204a.atasha204A_zone.OTP, 0, 0, False)
    otp_data_high = quest_marker.crypto.command_read(questMarker.atsha204a.atasha204A_zone.OTP, 1, 0, False)

    print("OTP low =", otp_data_low)
    print("OTP high =", otp_data_high)

    # check mac command succeds
    print("mac challenge 0", hexString(send_basic_challenge(quest_marker, 0)))
    print("mac challenge 1", hexString(send_basic_challenge(quest_marker, 1)))
    print("mac challenge 2", hexString(send_basic_challenge(quest_marker, 2)))
    print("mac challenge 3", hexString(send_basic_challenge(quest_marker, 3)))
    print("mac challenge 8", hexString(send_basic_challenge(quest_marker, 8)))
    print("mac challenge 9", hexString(send_basic_challenge(quest_marker, 9)))
    print("mac challenge 10", hexString(send_basic_challenge(quest_marker, 10)))
    print("mac challenge 11", hexString(send_basic_challenge(quest_marker, 11)))
    print("mac challenge 12", hexString(send_basic_challenge(quest_marker, 12)))
    print("mac challenge 13", hexString(send_basic_challenge(quest_marker, 13)))

    # check public reads
    print("read key 4", hexString(read_public_var(quest_maker, 4)))
    print("read key 5", hexString(read_public_var(quest_maker, 5)))
    print("read key 6", hexString(read_public_var(quest_maker, 6)))
    print("read key 7", hexString(read_public_var(quest_maker, 7)))

    # can write to readkeys with master key / submaster
    encrypted_write(quest_maker, 0x00, factoryData[0x00], 0x0F)
    encrypted_write(quest_maker, 0x01, factoryData[0x01], 0x0F)
    encrypted_write(quest_maker, 0x02, factoryData[0x02], 0x0E)
    encrypted_write(quest_maker, 0x03, factoryData[0x03], 0x0E)
    encrypted_write(quest_maker, 0x04, factoryData[0x04], 0x0E)
    encrypted_write(quest_maker, 0x05, factoryData[0x05], 0x0E)
    encrypted_write(quest_maker, 0x06, factoryData[0x06], 0x0E)
    encrypted_write(quest_maker, 0x07, factoryData[0x07], 0x0E)
    encrypted_write(quest_maker, 0x08, factoryData[0x08], 0x0F)
    encrypted_write(quest_maker, 0x09, factoryData[0x09], 0x0F)
    encrypted_write(quest_maker, 0x0A, factoryData[0x0A], 0x0E)
    encrypted_write(quest_maker, 0x0B, factoryData[0x0B], 0x0E)
    encrypted_write(quest_maker, 0x0C, factoryData[0x0C], 0x0E)
    encrypted_write(quest_maker, 0x0D, factoryData[0x0D], 0x0E)
    encrypted_write(quest_maker, 0x0E, factoryData[0x0E], 0x0F)

    try:
        encrypted_write(quest_maker, 0x00, factoryData[0x00], 0x0E)
    except:
        print("Sucessfully failed to write to slot 0x00 with key 0x0E")

    # can perform an encrypted read against key
    print("enc read key 8", hexString(encrypted_read(quest_maker, 0x08)))
    print("enc read key 10", hexString(encrypted_read(quest_maker, 0x0A)))
    print("enc read key 12", hexString(encrypted_read(quest_maker, 0x0C)))

    # check we cant challenge aginst wrong keys
    try:
        print("mac challenge E", hexString(send_basic_challenge(quest_marker, 0x0E)))
        print("ERROR performed mac on slot E")
    except RuntimeError:
        print("Sucessfuly failed to mac against slot E")

    try:
        print("mac challenge F", hexString(send_basic_challenge(quest_marker, 0x0F)))
        print("ERROR performed mac on slot F")
    except RuntimeError:
        print("Sucessfuly failed to mac against slot F")


@click.group()
@click.option('-s', '--secrets', type=click.Path(exists=True), default="secrets.json")
@click.pass_context
def cli(ctx, secrets):

    ctx.ensure_object(dict)

    with open(secrets) as file:
        raw_keys = json.load(file)
        keys = dict()
        for id in raw_keys:
            keys[bytearray.fromhex(id)[0]] = bytearray.fromhex(raw_keys[id])

    ctx.obj['keys'] = keys


@cli.command()
@click.pass_context
def perform_challenge(ctx):
    """
    Performs a test challenge against the chip
    and validates agaisnt the test server
    """
    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    chip_serial = quest_marker.crypto.get_serial_number()
    (chip_random, chip_response) = quest_marker.perform_challenge([0x00])

    print("chip: {}".format(hexString(chip_response)))

    expected_response = server_validator.badge_response_calculation(
        chip_serial,
        chip_random,
        [0x00]*20,
        ctx.obj['keys'][0x00])

    print("serv: {}".format(hexString(expected_response)))

    print(len(chip_response), len(expected_response))

    if chip_response == expected_response:
        print("Correct challenge recieved for {} at {}".format([0x00], hexString(chip_serial)))
        quest_marker.set_status_led(True)
    else:
        print("Incorrect challenge recieved for {} at {}".format([0x00], hexString(chip_serial)))
        quest_marker.set_status_led(False)


@cli.command()
@click.pass_context
def check_diversified_key(ctx):
    """
    Checks a diversified key in slot 0 is correct
    """
    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    div_key = quest_marker.crypto.generate_diversified_key(
        ctx.obj['keys'][0x00],
        0x00
    )

    print(hexString(div_key))

    quest_marker.crypto.check_key(0x00, div_key)


@cli.command
@click.argument("id")
@click.pass_context
def provision_single_hexpansion(ctx, id: int):
    """provisions a single hexpansion"""

    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    serial = int(id, 0)

    print("provisioning as {:04X}".format(serial))

    quest_marker.provision(ctx.obj['keys'], serial)

    print("provisioning complete")

    quest_marker.set_status_led(True)


if __name__ == "__main__":
    cli(obj={})

    # device = provisioner.provisioner()
    # quest_marker = questMarker.quest_marker(device)

    # div_key = quest_marker.crypto.generate_diversified_key(
    #     bytearray.fromhex(""),
    #     0x00
    # )

    # quest_marker.crypto.sendWake()

    # quest_marker.crypto.encrypted_write(
    #     0x00, div_key, 0x0F,
    #     bytearray.fromhex("")
    #     )

    # device.wait_for_detect()
    # (tests_passed, results) = quest_marker.basic_self_test(eeprom_write=True)
    # if not tests_passed:
    #     print("failed", results)
    # else:
    #     print("Passed")
    #     device.set_status_led(True)

    # device.wait_for_no_detect()

    # crypto_config_test(quest_marker)
    # quest_marker.provision()


    # device.set_status_led(False)
