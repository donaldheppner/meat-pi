import logging

class Board:
    def __init__(self):
        logging.info('Loading mock board')

    def get_value(self, pin):
        return 50000

    # def get_average_value(self, pin):
    #     return 50000

    def turn_on_relay(self):
        pass

    def turn_off_relay(self):
        pass