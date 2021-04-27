import math
import RPi.GPIO as GPIO
import time
import threading
import logging

# Using the Python Device SDK for IoT Hub:
#   https://github.com/Azure/azure-iot-sdk-python
# The sample connects to a device-specific MQTT endpoint on your IoT Hub.
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

# https://github.com/adafruit/Adafruit_CircuitPython_MCP3xxx
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

# The device connection string to authenticate the device with your IoT hub.
# Using the Azure CLI:
# az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
CONNECTION_STRING = "HostName=meat-hub.azure-devices.net;DeviceId=MyPythonDevice;SharedAccessKey=**TO READ FROM CONFIG**"


# create the spi bus
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# create the cs (chip select)
cs = digitalio.DigitalInOut(board.D5)

# create the mcp object
mcp = MCP.MCP3008(spi, cs)


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
            logging.debug('Calculating thermistor coefficients')
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
            logging.debug('Using default thermistor coefficients')
            # Default coefficients: https://tvwbb.com/threads/thermoworks-tx-1001x-op-tx-1003x-ap-probe-steinhart-hart-coefficients.69233/
            self.a = 0.0007343140544
            self.b = 0.0002157437229
            self.c = 0.0000000951568577

    def calculate_reading(self, adc):
        # https://learn.adafruit.com/thermistor/using-a-thermistor
        resistance = self.resistor / ((65535 / adc) - 1)
        lnResistance = math.log1p(resistance)
        kelvins = 1 / (self.a + (self.b * lnResistance) +
                       (self.c * (lnResistance ** 3)))

        return ThermistorReading(self, adc, resistance, kelvins)
    
    def reading(self):
        return self.calculate_reading(self.thermistor.value)


class Cooker:
    # A Cooker is defined as:
    # - 1 chamber probe and (up to) 3 food probes
    # - A target temperature for the chamber with a tolerance (in kelvin)
    # - A status, indicating if the cooker is heating
    # - A configuration used to convert ADC values to temperatures (kelvin)
    # up to 4 thermistors, [0] being the chamber
    def __init__(self, thermistors, chamber_target, chamber_tolerance=2.0):
        self.chamber_thermistor = thermistors[0]
        self.food_thermistors = thermistors[1:]
        self.chamber_target = chamber_target
        self.chamber_tolerance = chamber_tolerance

    def read_chamber(self):
        chan = AnalogIn(mcp, MCP.P0)
        logging.debug(
            f'Read chamber value of: {chan.value} and voltage of {chan.voltage}')


class Client:
    class Response:
        def __init__(self, payload, status):
            self.payload = payload
            self.status = status

    def __init__(self):
        self.client = IoTHubDeviceClient.create_from_connection_string(
            CONNECTION_STRING)

    def device_method_listener(device_client):
        method_request = device_client.receive_method_request()
        print(
            "\nMethod callback called with:\nmethodName = {method_name}\npayload = {payload}".format(
                method_name=method_request.name,
                payload=method_request.payload
            )
        )

        if method_request.name == "SetTelemetryInterval":
            try:
                INTERVAL = int(method_request.payload)
            except ValueError:
                response_payload = {"Response": "Invalid parameter"}
                response_status = 400
            else:
                response_payload = {
                    "Response": "Executed direct method {}".format(method_request.name)}
                response_status = 200
        else:
            response_payload = {
                "Response": "Direct method {} not defined".format(method_request.name)}
            response_status = 404

        method_response = MethodResponse(
            method_request.request_id, response_status, payload=response_payload)
        device_client.send_method_response(method_response)


def main():
    logging.basicConfig(level=logging.DEBUG)
    dud = AnalogIn(mcp, MCP.P1)
    food = AnalogIn(mcp, MCP.P2)
    none = AnalogIn(mcp, MCP.P6)

    chamber = Thermistor(mcp, MCP.P0)
    food = Thermistor(mcp, MCP.P2)

    while True:
        # print(f'Chamber: {chamber.value:5d}, {chamber.voltage:8f}V'
        #       f'Food:    {food.value:5d}, {food.voltage:8f}V'
        #       f'Dud:     {dud.value:5d}, {dud.voltage:8f}V'
        #       f'None:    {none.value:5d}, {none.voltage:8f}V')
        chamber_reading = chamber.reading()
        food_reading = food.reading()
        print(f'Value: {chamber_reading.value}, C: {chamber_reading.fahrenheit()} | Value: {food_reading.value}, C: {food_reading.fahrenheit()}')
        time.sleep(0.5)

    # cooker = Cooker([Thermistor(), Thermistor()], 80.0)
    # cooker.read_chamber()


if __name__ == '__main__':
    print("Starting Meat-Pi")
    print("Press Ctrl-C to exit")
    main()
