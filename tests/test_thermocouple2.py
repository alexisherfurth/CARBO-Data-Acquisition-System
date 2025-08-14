import board
import time
import digitalio

import adafruit_max31856

# Create sensor object, communicating over the board's default SPI bus
spi = board.SPI()

# allocate a CS pin and set the direction
cs = digitalio.DigitalInOut(board.D6)
cs.direction = digitalio.Direction.OUTPUT

# create a thermocouple object with the above
thermocouple = adafruit_max31856.MAX31856(spi, cs)
thermocouple.thermocouple_type = adafruit_max31856.ThermocoupleType.E

while True:
    temp_K = thermocouple.temperature + 273.15
    print(f"Temperature: {temp_K:.2f} K")
    print("Reference (Cold Junction) Temp:", thermocouple.reference_temperature + 273.15, "K")
    time.sleep(1)