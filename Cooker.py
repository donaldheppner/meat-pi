import math
import time
import threading
import logging
import json
import uuid

try:
    from Board import Board
except Exception as e:
    logging.info(f'Could not load Board: {e}')
    from MockBoard import Board

# https://github.com/adafruit/Adafruit_CircuitPython_MCP3xxx

def convert_fahrenheit_to_kelvins(f):
    return convert_fahrenheit_to_celcius(f) + 273.15

def convert_fahrenheit_to_celcius(f):
    return (f - 32) * 5 / 9

class CalibrationPoint:
    def __init__(self, resistance, temperature):
        self.resistance = resistance
        self.temperature = temperature

    def __lt__(self, other):
        return self.temperature < other.temperature


class ThermistorReading:
    def __init__(self, thermistor, value, resistance, kelvins):
        self.thermistor = thermistor
        self.value = value
        self.resistance = resistance
        self.kelvins = kelvins

    def celcius(self):
        return self.kelvins - 273.15

    def fahrenheit(self):
        return ((self.celcius() * 9) / 5) + 32
    
    def to_dict(self):
        return {
            'pin': self.thermistor.pin,
            'value': self.thermistor.value,
            'resistance': self.thermistor.resistance,
            'kelvins': self.thermistor.kelvins,
        }

class Thermistor:
    # calculates the coefficients based on the calibartion points
    def __init__(self, board, pin, calibration_points=[], resistor=10000, voltage_in=3.3):
        self.board = board
        self.pin = pin
        self.calibration_points = calibration_points
        self.resistor = resistor
        self.voltage_in = voltage_in

        # need 3 calibration points to do anything
        if(len(self.calibration_points) == 3):
            logging.debug(f'Calculating thermistor coefficients for pin {pin}')
            self.calibration_points.sort()

            # https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation, calulated coefficients
            l1 = math.log(calibration_points[0].resistance)
            l2 = math.log(calibration_points[1].resistance)
            l3 = math.log(calibration_points[2].resistance)

            logging.debug(f'R1: {calibration_points[0].resistance}, R2: {calibration_points[1].resistance}, R3: {calibration_points[2].resistance}')
            logging.debug(f'L1: {l1}, L2: {l2}, L3: {l3}')

            y1 = 1 / calibration_points[0].temperature
            y2 = 1 / calibration_points[1].temperature
            y3 = 1 / calibration_points[2].temperature

            logging.debug(f'Y1: {y1}, Y2: {y2}, Y3: {y3}')

            g2 = (y2-y1)/(l2-l1)
            g3 = (y3-y1)/(l3-l1)

            logging.debug(f'G2: {g2}, G3: {g3}')

            self.c = ((g3 - g2) / (l3 - l2)) * ((l1 + l2 + l3) ** -1)
            self.b = g2 - (self.c * ((l1 ** 2) + (l1 * l2) + (l2 ** 2)))
            self.a = y1 - ((self.b + ((l1 ** 2) * self.c)) * l1)

            logging.debug(f'Coefficients for pin {pin} = a: {self.a}, b: {self.b}, c: {self.c}')

        else:
            logging.debug(f'Using default thermistor coefficients for pin {pin}')
            # Default coefficients: https://tvwbb.com/threads/thermoworks-tx-1001x-op-tx-1003x-ap-probe-steinhart-hart-coefficients.69233/
            self.a = 0.0007343140544
            self.b = 0.0002157437229
            self.c = 0.0000000951568577

    def calculate_reading(self, adc):
        if(adc > 0):
            # https://learn.adafruit.com/thermistor/using-a-thermistor
            resistance = self.resistor / ((65535 / adc) - 1)
            lnResistance = math.log1p(resistance)
            kelvins = 1 / (self.a + (self.b * lnResistance) +
                        (self.c * (lnResistance ** 3)))
            return ThermistorReading(self, adc, resistance, kelvins)
        else:
            return ThermistorReading(self, 0, 0, 0)
    
    def reading(self):
        return self.calculate_reading(self.board.get_value(self.pin))
    
    def load_from_config(board, config):
        result = []
        data = json.loads(config)
        for calibration in data:
            pin = calibration['pin']
            points = [CalibrationPoint(p['resistance'], p['kelvins']) for p in calibration['points']]
            result.append(Thermistor(board, pin, points))
        
        return result


class Cooker:
    is_cooker_on = False
    last_cooker_on_time = 0

    COOKER_ON_DELAY = 120   # don't turn the cooker on if it was last turned less than X seconds ago

    # A Cooker is defined as:
    # - 1 chamber probe and (up to) 3 food probes (chamber is assumed to be index 0)
    # - A target temperature for the chamber with a tolerance (in kelvin)
    # - A status, indicating if the cooker is heating
    # - A configuration used to convert ADC values to temperatures (kelvin)
    # up to 4 thermistors, [0] being the chamber
    def __init__(self, board, thermistors, chamber_target=0.0, chamber_tolerance=2.0):
        self.cook_id = uuid.uuid4().hex
        self.board = board
        self.thermistors = thermistors
        self.chamber_target = chamber_target
        self.chamber_tolerance = chamber_tolerance

    # returns a reading from the chamber
    def read_chamber(self):
        return self.thermistors[0].reading()
    
    # returns a list of readings from the food probes
    def read_food(self):
        return [t.reading() for t in self.thermistors[1:]]
    
    def read_thermistors(self):
        return [t.reading() for t in self.thermistors]
    
    # returns a full-set of readings from the cook in an easy-to-serialize format
    def get_cook_reading(self, readings):
        return {
            'cook_id': self.cook_id,
            'chamber_target': self.chamber_target,
            'cooker_on': self.is_cooker_on,
            'readings': [t.to_dict() for t in readings]
        }

    def safe_to_turn_on(self):
        return time.time() > self.last_cooker_on_time + self.COOKER_ON_DELAY

    def cooker_on(self):
        if (not self.is_cooker_on) and self.safe_to_turn_on():
            logging.debug('Turning on cooker')
            # turn on the cooker
            self.board.turn_on_relay()
            self.is_cooker_on = True
            self.last_cooker_on_time = time.time()

    def cooker_off(self):
        if self.is_cooker_on:
            logging.debug('Turning off cooker')
            self.board.turn_off_relay()
            self.is_cooker_on = False
    
    def set_target_temperature_kelvins(self, kelvins):
        logging.debug(f'Setting target temperature to {kelvins}K')        
        # max is about 450 (350F), min is zero (always off)
        if kelvins <= 450:
            self.chamber_target = kelvins
        else:
            message = f'Target temperature outside of range: {kelvins}K'
            logging.error(message)
            raise ValueError(message)

    
    # expected to be called at an interval in a loop to maintain cooker temperature
    def update_cooker(self):
        readings = self.read_thermistors()
        chamber_temperature = readings[0]
        # if the chamber temperature is over target by tolerance amount, turn off the cooker
        if(chamber_temperature.kelvins > self.chamber_target + self.chamber_tolerance):
            self.cooker_off()
        # if the chamber temperature is below target by tolerance amount, turn on the cooker
        elif(chamber_temperature.kelvins < self.chamber_target - self.chamber_tolerance):
            self.cooker_on()
        
        return readings