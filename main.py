import math
import time
import threading
import logging
logging.basicConfig(level=logging.DEBUG)

# Using the Python Device SDK for IoT Hub:
#   https://github.com/Azure/azure-iot-sdk-python
# The sample connects to a device-specific MQTT endpoint on your IoT Hub.
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

from Cooker import Cooker, Thermistor

# the Board encapsulates all interactions with the Pi and hardware dependencies
try:
    from Board import Board
except Exception as e:
    logging.info(f'Could not load Board {e}')
    from MockBoard import Board


# The device connection string to authenticate the device with your IoT hub.
# Using the Azure CLI:
# az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
CONNECTION_STRING = "HostName=meat-hub.azure-devices.net;DeviceId=MyPythonDevice;SharedAccessKey=**TO READ FROM CONFIG**"


class Client:
    class Response:
        def __init__(self, payload, status):
            self.payload = payload
            self.status = status

    def __init__(self, cooker):
        self.client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        self.cooker = cooker

        # Start a thread to listen 
        device_method_thread = threading.Thread(target=device_method_listener, args=(self, client))
        device_method_thread.daemon = True
        device_method_thread.start()

    def device_method_listener(device_client):
        method_request = device_client.receive_method_request()
        print(
            "\nMethod callback called with:\nmethodName = {method_name}\npayload = {payload}".format(
                method_name=method_request.name,
                payload=method_request.payload
            )
        )

        if method_request.name == "SetTargetTemperature":
            try:
                target_temp = float(method_request.payload)
                
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
    b = Board()

    with open('calibration.json') as f:
        probes = Thermistor.load_from_config(b, f.read())

    cooker = Cooker(b, probes, 383.15)

    while True:
        # print(f'Chamber: {chamber.value:5d}, {chamber.voltage:8f}V'
        #       f'Food:    {food.value:5d}, {food.voltage:8f}V'
        #       f'Dud:     {dud.value:5d}, {dud.voltage:8f}V'
        #       f'None:    {none.value:5d}, {none.voltage:8f}V')
        chamber_reading = cooker.read_chamber()
        food_reading = cooker.read_food()[0]
        print(f'V: {chamber_reading.value}, R:{chamber_reading.resistance:,.0f} K: {chamber_reading.kelvins:.1f} F: {chamber_reading.fahrenheit():.1f} -'\
            f' V: {food_reading.value}, R:{food_reading.resistance:,.0f} K: {food_reading.kelvins:.1f} F: {food_reading.fahrenheit():.1f} ')

        cooker.cooker_on()
        time.sleep(0.5)
        cooker.cooker_off()

    # cooker = Cooker([Thermistor(), Thermistor()], 80.0)
    # cooker.read_chamber()


if __name__ == '__main__':
    print("Starting Meat-Pi")
    print("Press Ctrl-C to exit")
    main()
