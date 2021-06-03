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

def main():
    b = Board()


    while True:
        readings = ''
        for p in range(0, 8, 2):
            readings += f'{p}: R:{b.get_average_value(p):>12.2f}  '

        #print(f'\r{readings}', end='')
        print(readings)
        time.sleep(0)


if __name__ == '__main__':
    print('Starting Meat-Pi Calibration')
    print('Press Ctrl-C to exit')
    main()
