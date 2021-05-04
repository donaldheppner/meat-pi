from Cooker import Cooker, Thermistor
import math
import time
import threading
import logging
import os

# Using the Python Device SDK for IoT Hub:
#   https://github.com/Azure/azure-iot-sdk-python
# The sample connects to a device-specific MQTT endpoint on your IoT Hub.
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

logging.basicConfig(level=logging.DEBUG)

# the Board encapsulates all interactions with the Pi and hardware dependencies
try:
    from Board import Board
except Exception as e:
    logging.info(f'Could not load Board {e}')
    from MockBoard import Board


class Client:
    class Response:
        def __init__(self, payload, status):
            self.payload = payload
            self.status = status

    def __init__(self, cooker, device_id, shared_access_key):
        # The device connection string to authenticate the device with your IoT hub.
        # Using the Azure CLI:
        # az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
        connection_string = f'HostName=meat-hub.azure-devices.net;DeviceId={device_id};SharedAccessKey={shared_acces_key}'
        self.client = IoTHubDeviceClient.create_from_connection_string(
            connection_string)
        self.cooker = cooker

        # Start a thread to listen for incoming methods
        device_method_thread = threading.Thread(
            target=device_method_listener, args=(self, client))
        device_method_thread.daemon = True
        device_method_thread.start()

    def device_method_listener(device_client):
        method_request = device_client.receive_method_request()
        logging.debug(
            f'Method {method_request.name} called with payload: {method_request.payload}')

        if method_request.name == 'SetTargetTemperature':
            response = self.set_target_temperature(method_request.payload)
        else:
            response = Response(
                f'Direct method {method_request.name} is not defined', 404)

        method_response = MethodResponse(
            method_request.request_id, response.status, payload=response.payload)
        device_client.send_method_response(method_response)

    def set_target_temperature(self, payload):
        try:
            self.cooker.set_target_temperature_kelvins(
                float(method_request.payload))
        except ValueError:
            payload = {'Response': 'Invalid parameter'}
            status = 400
        else:
            payload = {
                'Response': f'Executed direct method {method_request.name}'}
            status = 200

        return Response(payload, status)


def load_config():
    # Load configuration
    LOCAL_CONFIG = 'device.local.json'
    CONFIG = 'device.json'
    configuration_file = ''
    if os.path.isfile('device.local.json'):
        configuration_file = LOCAL_CONFIG
    elif os.path.isfile('device.json'):
        configuration_file = CONFIG

    if len(configuraton_file) > 0:
        with open(configuration_file) as f:
            configuration = json.load(configuration_file)
    else:
        raise Exception('Configuration not found')

    return configuration


def load_probes():
    probes = []
    CALIBRATION_FILE = 'calibration.json'
    if os.path.isfile(CALIBRATION_FILE):
        with open(CALIBRATION_FILE) as f:
            probes = Thermistor.load_from_config(b, f.read())
    else:
        # load default probes
        logging.debug('No probe configuration found, loading default')
        probes = [Thermistor(b, p) for p in range(8) if x % 2 == 0]

    return probes


def main():
    INTERVAL = 5 # seconds
    b = Board()

    configuration = load_config()
    probles = load_probes()

    cooker = Cooker(b, probes)
    client = Client(cooker, configuration['device_id'], configuration['sak'])

    # main thread to run the cook
    while True:
        readings = cooker.update_cooker()
        cook_readings = cooker.get_cook_reading(readings)

        logging.debug(f'Cook readings: {cook_readings}')

        # send the readings for the cook
        client.send_message(json.dumps(cook_readings))
        thread.sleep(INTERVAL)


if __name__ == '__main__':
    print("Starting Meat-Pi")
    print("Press Ctrl-C to exit")
    main()
