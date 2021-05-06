import math
import time
import threading
import logging
import json
import uuid

logging.basicConfig(level=logging.DEBUG)


try:
    from Board import Board
except Exception as e:
    logging.info(f'Could not load Board: {e}')
    from MockBoard import Board

from Cooker import Thermistor

def main():
    b = Board()
    thermistors = [Thermistor(b, p) for p in range(8) if p % 2 == 0]

    while True:
        readings = ''
        for t in thermistors:
            r = t.reading()
            readings += f'{t.pin}: R:{r.resistance:7.2f}  '

        print(f'\r{readings}', end='')
        time.sleep(.1)


if __name__ == '__main__':
    print('Starting Meat-Pi Calibration')
    print('Press Ctrl-C to exit')
    main()
