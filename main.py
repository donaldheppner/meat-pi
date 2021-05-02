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

from Cooker import Cooker, Thermistor

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


class Client:
    class Response:
        def __init__(self, payload, status):
            self.payload = payload
            self.status = status

    def __init__(self):
        self.client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

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

    probes = [Thermistor(mcp, MCP.P0), Thermistor(mcp, MCP.P2), Thermistor(mcp, MCP.P4), Thermistor(mcp, MCP.P6)]
    cooker = Cooker(probes, 383.15)

    while True:
        # print(f'Chamber: {chamber.value:5d}, {chamber.voltage:8f}V'
        #       f'Food:    {food.value:5d}, {food.voltage:8f}V'
        #       f'Dud:     {dud.value:5d}, {dud.voltage:8f}V'
        #       f'None:    {none.value:5d}, {none.voltage:8f}V')
        chamber_reading = cooker.read_chamber()
        food_reading = cooker.read_food()[0]
        print(f'C: {chamber_reading.value}, C: {chamber_reading.fahrenheit()} | Value: {food_reading.value}, C: {food_reading.fahrenheit()}')

        cooker.cooker_on()
        time.sleep(0.5)
        cooker.cooker_off()

    # cooker = Cooker([Thermistor(), Thermistor()], 80.0)
    # cooker.read_chamber()


if __name__ == '__main__':
    print("Starting Meat-Pi")
    print("Press Ctrl-C to exit")
    main()
