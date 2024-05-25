

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
