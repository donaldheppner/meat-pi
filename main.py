import math
import time
import threading
import logging
import os
import json

# Using the Python Device SDK for IoT Hub:
#   https://github.com/Azure/azure-iot-sdk-python
# The sample connects to a device-specific MQTT endpoint on your IoT Hub.
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

#logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler('cooker.log', encoding='utf-8')])
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
logging.getLogger(__name__).setLevel(logging.DEBUG)

from Cooker import Cooker, Thermistor

# the Board encapsulates all interactions with the Pi and hardware dependencies
try:
    from Board import Board
except Exception as e:
    logging.info(f'Could not load Board: {e}')
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
        connection_string = f'HostName=meat-hub.azure-devices.net;DeviceId={device_id};SharedAccessKey={shared_access_key}'
        self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)
        self.device_id = device_id
        self.cooker = cooker

        # Start a thread to listen for incoming methods
        device_method_thread = threading.Thread(
            target=Client.device_method_listener, args=(self, self.client))
        device_method_thread.daemon = True
        device_method_thread.start()
    
    def send_message(self, message):
        self.client.send_message(message)

    def device_method_listener(self, device_client):
        while True:
            method_request = device_client.receive_method_request()
            logging.debug(
                f'Method {method_request.name} called with payload: {method_request.payload}')

            if method_request.name == 'SetTargetTemperature':
                response = self.set_target_temperature(method_request)
            else:
                response = Response(
                    f'Direct method {method_request.name} is not defined', 404)

            method_response = MethodResponse(
                method_request.request_id, response.status, payload=response.payload)
            device_client.send_method_response(method_response)

    def set_target_temperature(self, method_request):
        try:
            self.cooker.set_target_temperature_kelvins(float(method_request.payload))
        except ValueError:
            payload = {'Response': 'Invalid parameter'}
            status = 400
        else:
            payload = {
                'Response': f'Executed direct method {method_request.name}'}
            status = 200

        return MethodResponse(payload, status)


def load_config():
    # Load configuration
    LOCAL_CONFIG = 'device.local.json'
    CONFIG = 'device.json'
    configuration_file = ''
    if os.path.isfile(CONFIG):
        configuration_file = CONFIG
    elif os.path.isfile(LOCAL_CONFIG):
        configuration_file = LOCAL_CONFIG

    if len(configuration_file) > 0:
        with open(configuration_file) as f:
            configuration = json.load(f)
    else:
        raise Exception('Configuration not found')

    return configuration


def load_probes(board):
    probes = []
    CALIBRATION_FILE = 'calibration.json'
    if os.path.isfile(CALIBRATION_FILE):
        with open(CALIBRATION_FILE) as f:
            probes = Thermistor.load_from_config(board, f.read())
    else:
        # load default probes
        logging.debug('No probe configuration found, loading default')
        probes = [Thermistor(board, p) for p in range(8) if p % 2 == 0]

    return probes


def main():
    INTERVAL = 25 # seconds
    b = Board()

    configuration = load_config()
    probes = load_probes(b)

    cooker = Cooker(b, probes)
    client = Client(cooker, configuration['device_id'], configuration['sak'])

    try:
        # main thread to run the cook
        while True:
            readings = cooker.update_cooker()
            cook_readings = cooker.get_cook_reading(readings)
            cook_readings['device_id'] = client.device_id

            logging.info(f'Cook readings: {cook_readings}')

            # send the readings for the cook
            client.send_message(json.dumps(cook_readings))
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print('Exiting the MeatPi')
    finally:
        cooker.cooker_off()


if __name__ == '__main__':
    try:
        print('Starting MeatPi')
        print('Press Ctrl-C to exit')
        main()
    except KeyboardInterrupt:
        print('Exiting the MeatPi')
