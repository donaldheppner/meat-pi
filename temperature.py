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
    L1 = math.log(128378)     # freezing
    L2 = math.log(77521)     # room temp
    L3 = math.log(7239)       # boiling

    Y1 = 1 / 280.93             # freezing as recorded
    Y2 = 1 / 297.15             # room as recorded
    Y3 = 1 / 368.15             # boiling as recorded

    G2 = (Y2-Y1)/(L2-L1)
    G3 = (Y3-Y1)/(L3-L1)

    C = ((G3 - G2) / (L3-L2)) * ((L1 + L2 + L3) ** -1)
    B = G2 - C * ((L1 ** 2) + L1 * L2 + (L2 ** 2))
    A = Y1 - (B + (L1 ** 2) * C) * L1

    print("A:", str(A))
    print("B:", str(B))
    print("C:", str(C))

    voltageOut = voltageIn - ((adc * voltageIn) / 1024)
    print("Voltage:", str(voltageOut))

    # https://electronics.stackexchange.com/questions/317132/converting-analog-10-bit-thermistor-reading-mcp3008-to-temperature
    resistance = ((voltageIn * R) - (voltageOut * R)) / voltageOut
    print("Resistance:", str(resistance), "for ADC:", str(adc))

    lnResistance = math.log1p(resistance)
    temperatureKelvin = 1 / (A + (B * lnResistance) +
                             (C * (lnResistance ** 3)))
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
