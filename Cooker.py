import math
import RPi.GPIO as GPIO
import time
import threading
import logging

# https://github.com/adafruit/Adafruit_CircuitPython_MCP3xxx
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn


class CalibrationPoint:
    def __init__(self, resistance, temperature):
        self.resistance = resistance
        self.temperature = temperature

    def __lt__(self, other):
        return self.resistance < other.resistance


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


class Thermistor:
    # calculates the coefficients based on the calibartion points
    def __init__(self, mcp, pin, calibration_points=[], resistor=10000, voltage_in=3.3):
        self.thermistor = AnalogIn(mcp, pin)
        self.calibration_points = calibration_points
        self.resistor = resistor
        self.voltage_in = voltage_in

        # need 3 calibration points to do anything
        if(len(self.calibration_points) == 3):
            logging.debug(f'Calculating thermistor coefficients for pin {pin}')
            self.calibration_points.sort(reverse=True)

            # https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation, calulated coefficients
            l1 = math.log1p(calibration_points[0].resistance)
            l2 = math.log1p(calibration_points[1].resistance)
            l3 = math.log1p(calibration_points[2].resistance)

            y1 = 1 / calibration_points[0].temperature
            y2 = 1 / calibration_points[1].temperature
            y3 = 1 / calibration_points[2].temperature

            g2 = (y2-y1)/(l2-l1)
            g3 = (y3-y1)/(l3-l1)

            self.c = ((g3 - g2) / (l3 - l2)) * ((l1 + l2 + l3) ** -1)
            self.b = g2 - self.c * ((l1 ** 2) + (l1 * l2) + (l2 ** 2))
            self.a = y1 - ((self.b + ((l1 ** 2) * self.c)) * l1)
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
        return self.calculate_reading(self.thermistor.value)

class Cooker:
    is_cooker_on = False
    last_cooker_on_time = 0

    COOKER_ON_DELAY = 120   # don't turn the cooker on if it was last turned less than X seconds ago
    COOKER_PIN = digitalio.DigitalInOut(board.D18)
    COOKER_PIN.direction = digitalio.Direction.OUTPUT

    # A Cooker is defined as:
    # - 1 chamber probe and (up to) 3 food probes (chamber is assumed to be index 0)
    # - A target temperature for the chamber with a tolerance (in kelvin)
    # - A status, indicating if the cooker is heating
    # - A configuration used to convert ADC values to temperatures (kelvin)
    # up to 4 thermistors, [0] being the chamber
    def __init__(self, thermistors, chamber_target, chamber_tolerance=2.0):
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

    def safe_to_turn_on(self):
        return time.time() > self.last_cooker_on_time + self.COOKER_ON_DELAY

    def cooker_on(self):
        if((not self.is_cooker_on) and self.safe_to_turn_on()):
            logging.debug('Turning on cooker')
            # turn on the cooker
            self.COOKER_PIN.value = True
            self.is_cooker_on = True
            self.last_cooker_on_time = time.time()

    def cooker_off(self):
        if(self.is_cooker_on):
            logging.debug('Turning off cooker')
            self.COOKER_PIN.value = False
            self.is_cooker_on = False
    
    # expected to be called at an interval in a loop to maintain cooker temperature
    def update_cooker(self):
        chamber_temperature = self.read_chamber()
        # if the chamber temperature is over target by tolerance amount, turn off the cooker
        if(chamber_temperature.kelvins > self.chamber_target + self.chamber_tolerance):
            self.cooker_off()
        # if the chamber temperature is below target by tolerance amount, turn on the cooker
        elif(chamber_temperature.kelvins < self.chamber_target - self.chamber_tolerance):
            self.cooker_on()