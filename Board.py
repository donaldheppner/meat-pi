import digitalio
import board
import busio
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

class Board:
    # create the spi bus
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

    # create the cs (chip select)
    cs = digitalio.DigitalInOut(board.D5)

    # create the mcp object
    mcp = MCP.MCP3008(spi, cs)


    RELAY_PIN = digitalio.DigitalInOut(board.D18)
    RELAY_PIN.direction = digitalio.Direction.OUTPUT

    inputs = {}

    def __init__(self):
        pass

    def get_value(self, pin):
        def get_pin():
            if(pin == 0):
                return MCP.P0
            elif(pin == 2):
                return MCP.P2
            elif(pin == 4):
                return MCP.P4
            elif(pin == 6):
                return MCP.P6
            else:
                raise ValueError(f'Invalid pin: {pin}')

        if pin not in self.inputs:
            self.inputs[pin] = AnalogIn(self.mcp, get_pin())
        
        return self.inputs[pin].value
    
    def turn_on_relay(self):
        self.RELAY_PIN.value = True

    def turn_off_relay(self):
        self.RELAY_PIN.value = False
