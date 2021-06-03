import math
import sys


def temp_calc(adc):
    R = 10000  # 10K Ohm resistor
    voltageIn = 3.3

    # Coefficients: https://tvwbb.com/threads/thermoworks-tx-1001x-op-tx-1003x-ap-probe-steinhart-hart-coefficients.69233/
    # A =  0.0007343140544
    # B =  0.0002157437229
    # C =  0.0000000951568577

    # https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation, calulated coefficients
    l1 = math.log(96600)
    l2 = math.log(34050)
    l3 = math.log(6180)

    print(f'L1: {l1}, L2: {l2}, L3: {l3}')

    y1 = 1 / 298.15
    y2 = 1 / 323.15
    y3 = 1 / 373.15

    print(f'Y1: {y1}, Y2: {y2}, Y3: {y3}')

    g2 = (y2-y1)/(l2-l1)
    g3 = (y3-y1)/(l3-l1)

    print(f'G2: {g2}, G3: {g3}')

    c = ((g3 - g2) / (l3 - l2)) * ((l1 + l2 + l3) ** -1)
    b = g2 - (c * ((l1 ** 2) + (l1 * l2) + (l2 ** 2)))
    a = y1 - ((b + ((l1 ** 2) * c)) * l1)

    print("A:", str(a))
    print("B:", str(b))
    print("C:", str(c))

    voltageOut = voltageIn - ((adc * voltageIn) / 1024)
    print("Voltage:", str(voltageOut))

    # https://electronics.stackexchange.com/questions/317132/converting-analog-10-bit-thermistor-reading-mcp3008-to-temperature
    resistance = ((voltageIn * R) - (voltageOut * R)) / voltageOut
    print("Resistance:", str(resistance), "for ADC:", str(adc))

    lnResistance = math.log1p(resistance)
    temperatureKelvin = 1 / (a + (b * lnResistance) +
                             (c * (lnResistance ** 3)))
    temperatureCelcius = temperatureKelvin - 273.15
    temperatureFarenheit = ((temperatureCelcius * 9) / 5) + 32

    return temperatureFarenheit

    # volts = (value * 3.3) / 1023 #calculate the voltage
    # print("Volts: ", str(volts))
    # ohms = ((1/volts)*3300)-100000 #calculate the ohms of the thermististor
    # print("Ohms: ", str(ohms))

    # lnohm = math.log1p(ohms) #take ln(ohms)

    # #a, b, & c values from http://www.thermistor.com/calculators.php
    # #using curve R (-6.2%/C @ 25C) Mil Ratio X
    # #a =  0.002197222470870
    # #b =  0.000161097632222
    # #c =  0.000000125008328

    # # Steinhart Hart Equation
    # # T = 1/(a + b[ln(ohm)] + c[ln(ohm)]^3)

    # t1 = (b*lnohm) # b[ln(ohm)]

    # c2 = c*lnohm # c[ln(ohm)]

    # t2 = math.pow(c2,3) # c[ln(ohm)]^3

    # temp = 1/(a + t1 + t2) #calcualte temperature

    # tempc = temp - 273.15 #K to C

    # tempf = tempc*9/5 + 32
    # # the -4 is error correction for bad python math

    # #print out info
    # #print ("%4d/1023 => %5.3f V => %4.1f ohms  => %4.1f K => %4.1f C  => %4.1f F" % (value, volts, ohms, temp, tempc, tempf))

    # return tempf


print("Temperature: ", str(temp_calc(float(sys.argv[1]))))
