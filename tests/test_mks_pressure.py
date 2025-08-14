import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADS object and specify the gain
ads = ADS.ADS1115(i2c)
ads.gain = 1
chan = AnalogIn(ads, ADS.P0)

# Continuously print the values
while True:
    print(f"Voltage: {chan.voltage}V")
    # Convert the voltage to pressure in Torr
    # Using voltage divider formula: V_out = V_in * (R2 / (R1 + R2))
    # Assuming R1 = 100k ohm and R2 = 100k ohm
    voltage_in = 1.00262198 * chan.voltage * (10**5 + 10**5) / 10**5
    print(f"MKS Voltage: {voltage_in}V")
    pressure = 10**(2*voltage_in - 11)
    print(f"Pressure: {pressure} Torr") 
    time.sleep(1)