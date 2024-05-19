import provisioner
import pyftdi
import questMarker


def hexString(data):
    """Converts data into a hex string for printing"""
    return ' '.join('{:02x}'.format(x) for x in data)


if __name__ == "__main__":
    device = provisioner.provisioner()
    quest_marker = questMarker.quest_marker(device)

    device.wait_for_detect()
    (tests_passed, results) = quest_marker.basic_self_test(eeprom_write=True)
    if not tests_passed:
        print("failed", results)
    else:
        print("Passed")
        device.set_status_led(True)

    device.wait_for_no_detect()
    device.set_status_led(False)
