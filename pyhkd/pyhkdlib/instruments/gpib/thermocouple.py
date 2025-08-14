"""
Thermocouple Interface via MAX31856

This module provides a class to interface with a thermocouple sensor
using the Adafruit MAX31856 over SPI. The temperature is read in Celsius
and converted to Kelvin.

Example usage:
    from pyhkdlib.instruments.gpib.thermocouple import ThermocoupleMAX31856
    tc = ThermocoupleMAX31856(cs_pin=board.D5, thermocouple_type="E")
    print(tc.get_temperature())
"""

import time
import logging
import board
import digitalio
import adafruit_max31856

from ..instrument import Instrument
from pyhkdlib.sensor import Sensor

class ThermocoupleMAX31856(Instrument):
    """
    Interface for a thermocouple sensor read via MAX31856.
    """
    NUM_SENSORS = 1
    BOX_TYPE = 'MAX31856'

    def __init__(self, cs_pin=board.D5, thermocouple_type="E", wait_time=1, channels=None, **kwargs):
        # Set up SPI
        self.spi = board.SPI()
        if isinstance(cs_pin, str):
            cs_pin = getattr(board, cs_pin)
        self.cs = digitalio.DigitalInOut(cs_pin)
        self.cs.direction = digitalio.Direction.OUTPUT
        self.thermocouple = adafruit_max31856.MAX31856(self.spi, self.cs)
        # Set thermocouple type
        self.thermocouple.thermocouple_type = getattr(adafruit_max31856.ThermocoupleType, thermocouple_type)
        self.wait_time = wait_time

        if channels is None:
            channels = [{"name": "Thermocouple 1", "type": "temperature"}]
        super().__init__(channels=channels, wait_time=wait_time, **kwargs)
        logging.info("ThermocoupleMAX31856 initialized.")

    def read_temperature_kelvin(self):
        # Read temperature in Celsius and convert to Kelvin
        temp_C = self.thermocouple.temperature
        temp_K = temp_C + 273.15
        return temp_K

    def read_reference_kelvin(self):
        # Read cold junction temperature in Celsius and convert to Kelvin
        ref_C = self.thermocouple.reference_temperature
        ref_K = ref_C + 273.15
        return ref_K

    def get_temperature(self):
        return self.read_temperature_kelvin()

    def update_periodic(self):
        temp_K = self.read_temperature_kelvin()
        sensor = self.get_sensor(0, Sensor.TYPE_TEMPERATURE, none_on_fail=True)
        if sensor is not None:
            sensor.value = temp_K

# Example script usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tc = ThermocoupleMAX31856()
    while True:
        temp_K = tc.get_temperature()
        ref_K = tc.read_reference_kelvin()
        print(f"Temperature: {temp_K:.2f} K")
        print(f"Reference (Cold Junction) Temp: {ref_K:.2f} K")
        time.sleep(1)