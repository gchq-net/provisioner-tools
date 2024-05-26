# import requests
import time
import requests
import utils
from uuid import UUID


def hexString(data):
    """Converts data into a hex string for printing"""
    return ' '.join('{:02x}'.format(x) for x in data)


def auto_retry(function: callable, retries: int, *args, **kwargs):
    """automatialy retries a command in the event of I2C failures"""

    for x in range(retries):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            if (x == retries-1):
                raise e


def submit_hexpansion(human_name: str, eeprom_serial: int, atsha_serial: int, api_key: str, api_server) -> None:

    payload = {
        "human_identifier": human_name,
        "eeprom_serial_number": eeprom_serial,
        "serial_number": str(UUID(int=atsha_serial)),
    }

    try:
        resp = requests.post(
            f"https://{api_server}/api/hexpansions/",
            json=payload,
            headers={"Accept": "application/json", "Authorization": f"Token {api_key}"},
            timeout=5,
        )
        if resp.status_code != 201:
            print(resp.json())
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"Failed to submit Hexpansion {human_name} to server: {e}")


def register_provision(board_serial, atsha_serial, api_key, log_file="provision.log", api_server="gchq.net"):

    with open(log_file, "a") as provision_log:
        provision_log.write("{:04X},{},{}\n".format(
            board_serial, utils.hexString(atsha_serial), time.strftime("%Y-%m-%d %H:%M:%S")
            ))

    if api_key is not None:
        submit_hexpansion(
            "{:04X}".format(board_serial),
            board_serial,
            int.from_bytes(atsha_serial, 'little'),
            api_key,
            api_server
            )
