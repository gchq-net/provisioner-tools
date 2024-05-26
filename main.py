import click
import json
import provisioner
import questMarker
import server_validator
import time
import utils
from utils import hexString


@click.group()
@click.option('-s', '--secrets', type=click.Path(exists=True), default="secrets.json")
@click.option('--api-key')
@click.pass_context
def cli(ctx, secrets, api_key):

    ctx.ensure_object(dict)

    with open(secrets) as file:
        raw_keys = json.load(file)
        keys = dict()
        for id in raw_keys:
            keys[bytearray.fromhex(id)[0]] = bytearray.fromhex(raw_keys[id])

    ctx.obj['keys'] = keys
    ctx.obj['api_key'] = api_key


@cli.command()
@click.pass_context
def crypto_config_test(ctx):
    """Performs checks on the config of the crypto IC"""

    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    # check OTP read
    otp_data_low = utils.auto_retry(
        quest_marker.crypto.command_read, 5,
        questMarker.atsha204a.atasha204A_zone.OTP, 0, 0, False)
    otp_data_high = utils.auto_retry(
        quest_marker.crypto.command_read, 5,
        questMarker.atsha204a.atasha204A_zone.OTP, 1, 0, False)

    print("OTP low =", otp_data_low)
    print("OTP high =", otp_data_high)

    # check mac command succeds
    print("mac challenge 0", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 0, [0x00]*32)))
    print("mac challenge 1", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 1, [0x00]*32)))
    print("mac challenge 2", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 2, [0x00]*32)))
    print("mac challenge 3", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 3, [0x00]*32)))
    print("mac challenge 8", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 8, [0x00]*32)))
    print("mac challenge 9", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 9, [0x00]*32)))
    print("mac challenge 10", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 10, [0x00]*32)))
    print("mac challenge 11", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 11, [0x00]*32)))
    print("mac challenge 12", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 12, [0x00]*32)))
    print("mac challenge 13", hexString(utils.auto_retry(quest_marker.crypto.command_mac, 5, 13, [0x00]*32)))

    # check public reads
    print("read key 4", hexString(utils.auto_retry(
        quest_marker.crypto.command_read, 5,
        questMarker.atsha204a.atasha204A_zone.DATA, 4, 0, False)))
    print("read key 5", hexString(utils.auto_retry(
        quest_marker.crypto.command_read, 5,
        questMarker.atsha204a.atasha204A_zone.DATA, 5, 0, False)))
    print("read key 6", hexString(utils.auto_retry(
        quest_marker.crypto.command_read, 5,
        questMarker.atsha204a.atasha204A_zone.DATA, 6, 0, False)))
    print("read key 7", hexString(utils.auto_retry(
        quest_marker.crypto.command_read, 5,
        questMarker.atsha204a.atasha204A_zone.DATA, 7, 0, False)))

    # can write to readkeys with master key / submaster

    write_mapping = {
        0x00: 0x0F,
        0x01: 0x0F,
        0x02: 0x0E,
        0x03: 0x0E,
        0x04: 0x0E,
        0x05: 0x0E,
        0x06: 0x0E,
        0x07: 0x0E,
        0x08: 0x0F,
        0x09: 0x0F,
        0x0A: 0x0E,
        0x0B: 0x0E,
        0x0C: 0x0E,
        0x0D: 0x0E,
        0x0E: 0x0F,
    }

    for slot in write_mapping:

        utils.auto_retry(
            quest_marker.crypto.encrypted_write, 5,
            slot, ctx.obj['keys'][slot],
            write_mapping[slot], ctx.obj['keys'][write_mapping[slot]]
            )
        print("Wrote data to slot {} with key {}".format(hex(slot), hex(write_mapping[slot])))

    try:
        utils.auto_retry(
            quest_marker.crypto.encrypted_write, 5,
            0, ctx.obj['keys'][0],
            write_mapping[0], ctx.obj['keys'][0]
            )
    except Exception:
        print("Sucessfully failed to write to slot 0x00 with key 0x0E")

    # can perform an encrypted read against key
    read_mapping = {
        0x08: 0x09,
        0x0A: 0x0B,
        0x0C: 0x0D,
    }

    for slot in read_mapping:
        read_data = utils.auto_retry(
            quest_marker.crypto.encrypted_read, 5,
            slot, read_mapping[slot], ctx.obj['keys'][read_mapping[slot]]
            )
        print("enc read key {}".format(slot), hexString(read_data))

    # check we cant challenge aginst wrong keys
    try:
        print("mac challenge E", hexString(utils.auto_retry(
            quest_marker.crypto.command_mac, 5,
            0x0E, [0x00]*32)))
        print("ERROR performed mac on slot E")
    except RuntimeError:
        print("Sucessfuly failed to mac against slot E")

    try:
        print("mac challenge F", hexString(utils.auto_retry(
            quest_marker.crypto.command_mac, 5,
            0x0F, [0x00]*32)))
        print("ERROR performed mac on slot F")
    except RuntimeError:
        print("Sucessfuly failed to mac against slot F")


@cli.command()
@click.pass_context
def perform_challenge(ctx):
    """
    Performs a test challenge against the chip
    and validates agaisnt the test server
    """
    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    badge_mac = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    chip_serial = quest_marker.crypto.get_serial_number()
    (chip_random, chip_response) = quest_marker.perform_challenge(badge_mac)

    print("chip: {}".format(hexString(chip_response)))

    expected_response = server_validator.badge_response_calculation(
        chip_serial,
        chip_random,
        badge_mac,
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

    device.set_status_led(False)

    serial = int(id, 0)

    print("provisioning as {:04X}".format(serial))

    quest_marker.provision(ctx.obj['keys'], serial)

    print("provisioning complete")

    atsha_serial = utils.auto_retry(quest_marker.crypto.get_serial_number, 5)

    device.set_status_led(True)
    utils.register_provision(serial, atsha_serial, ctx.obj['api_key'])


@cli.command
@click.argument("starting-id")
@click.pass_context
def provision_multiple_hexpansions(ctx, starting_id: str):
    """provisions a set of hexpansions"""

    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    serial = int(starting_id, 0)

    while True:

        print("provisioning next as {:04X}".format(serial))

        device.wait_for_detect()
        time.sleep(0.5)

        try:
            quest_marker.provision(ctx.obj['keys'], serial)

            print("provisioning complete ({:04X})".format(serial))

            atsha_serial = utils.auto_retry(quest_marker.crypto.get_serial_number, 5)

            utils.register_provision(serial, atsha_serial, ctx.obj['api_key'])

            checks = quest_marker.check_config(ctx.obj['keys'])

            if checks:
                print("checks passed")
            else:
                print("Config checks failed ({:04X})".format(serial))

            device.set_status_led(True)
        except Exception as e:
            print("FAILED TO PROVISION ({:04X})".format(serial))
            print(e)

        device.wait_for_no_detect()
        device.set_status_led(False)
        serial += 1


@cli.command
@click.pass_context
def set_diversified_key(ctx):
    """diversifies the slot 0 key"""

    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    div_key = quest_marker.crypto.generate_diversified_key(
        ctx.obj['keys'][0x00],
        0x00
        )

    quest_marker.crypto.sendWake()

    quest_marker.crypto.encrypted_write(
        0x00, div_key, 0x0F,
        ctx.obj['keys'][0x0F]
        )

    print("Diversified key set for slot 0")


@cli.command
@click.pass_context
def check_config(ctx):
    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    board_serial, atsha_serial = quest_marker.get_serial_numbers()

    print("checking {:04X} (atsha: {})".format(board_serial, hexString(atsha_serial)))

    passed = quest_marker.check_config(ctx.obj['keys'])

    if passed:
        print("Config is correct")
    else:
        print("configuration mismatch")


@cli.command
@click.pass_context
def update_config(ctx):
    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    board_serial, atsha_serial = quest_marker.get_serial_numbers()

    print("updating {:04X} (atsha: {})".format(board_serial, hexString(atsha_serial)))

    quest_marker.update(ctx.obj['keys'])


@cli.command
@click.argument("board_sn")
@click.argument("atsha_sn")
@click.pass_context
def register_provision(ctx, board_sn, atsha_sn):

    board_serial = int(board_sn, 0)
    atsha_serial = bytearray.fromhex(atsha_sn)

    utils.register_provision(board_serial, atsha_serial, ctx.obj['api_key'])


if __name__ == "__main__":
    cli(obj={})

    # device.wait_for_detect()
    # (tests_passed, results) = quest_marker.basic_self_test(eeprom_write=True)
    # if not tests_passed:
    #     print("failed", results)
    # else:
    #     print("Passed")
    #     device.set_status_led(True)

    # device.wait_for_no_detect()

    # crypto_config_test(quest_marker)

    # device.set_status_led(False)
