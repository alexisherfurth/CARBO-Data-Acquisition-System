"""
Lake Shore Model 224 Temperature Monitor Interface

This module provides a class to interface with the Lake Shore Model 224,
which measures up to 12 temperature sensor channels (A, B, C1-5, D1-5).

See the Lake Shore documentation for full command/query details.

Example usage:
    from lakeshore import Model224
    ls224 = Model224(com_port='/dev/ttyUSB0')
    temp = ls224.get_kelvin_reading('A')
"""

import logging
from lakeshore import Model224
from ..instrument import Instrument

LS224_CHANNELS = ['A', 'B', 'C1', 'C2', 'C3', 'C4', 'C5', 'D1', 'D2', 'D3', 'D4', 'D5']

class LakeShore224Interface(Instrument):
    """
    Interface for the Lake Shore Model 224 Temperature Monitor.
    """
    NUM_SENSORS = len(LS224_CHANNELS)
    BOX_TYPE = 'LS224'
    def __init__(self, port='/dev/ttyUSB0', baud_rate=57600, timeout=2.0, wait_time=8, channels=[], **kwargs):
        if channels is None:
            channels = [{"name": ch, "type": "temperature"} for ch in LS224_CHANNELS]
        super().__init__(channels=channels, wait_time=wait_time, **kwargs)
        self.instrument = Model224(com_port=port, baud_rate=baud_rate, timeout=timeout)
        logging.info("Lake Shore 224 initialized on port %s", port)

    def get_all_kelvin(self):
        """
        Returns a dictionary of all channel readings in Kelvin.
        """
        readings = {}
        for ch in LS224_CHANNELS:
            try:
                readings[ch] = self.instrument.get_kelvin_reading(ch)
            except Exception as e:
                logging.error("Error reading channel %s: %s", ch, e)
                readings[ch] = None
        return readings

    def get_all_celsius(self):
        """
        Returns a dictionary of all channel readings in Celsius.
        """
        readings = {}
        for ch in LS224_CHANNELS:
            try:
                readings[ch] = self.instrument.get_celsius_reading(ch)
            except Exception as e:
                logging.error("Error reading channel %s: %s", ch, e)
                readings[ch] = None
        return readings

    def get_status(self, channel):
        """
        Returns the reading status for a given channel.
        """
        try:
            return self.instrument.get_reading_status(channel)
        except Exception as e:
            logging.error("Error getting status for channel %s: %s", channel, e)
            return None

    def set_sensor_name(self, channel, name):
        """
        Sets a user-defined name for a sensor channel.
        """
        try:
            self.instrument.set_sensor_name(channel, name)
            logging.info("Set name for channel %s to %s", channel, name)
        except Exception as e:
            logging.error("Error setting name for channel %s: %s", channel, e)

    def get_sensor_name(self, channel):
        """
        Gets the user-defined name for a sensor channel.
        """
        try:
            return self.instrument.get_sensor_name(channel)
        except Exception as e:
            logging.error("Error getting name for channel %s: %s", channel, e)
            return None

    def reset_instrument(self):
        """
        Resets the instrument to power-up settings.
        """
        try:
            self.instrument.reset_instrument()
            logging.info("Instrument reset to factory settings.")
        except Exception as e:
            logging.error("Error resetting instrument: %s", e)

    def update_periodic(self):
        readings = self.get_all_kelvin()
        for ch in LS224_CHANNELS:
            # Find the channel id for this channel name
            chan_id = ch
            # Update the sensor value for this channel
            sensor = self.get_sensor(chan_id, "temperature", none_on_fail=True)
            if sensor is not None:
                val = readings.get(ch)
                if val is not None:
                    sensor.value = val

# Example script usage
if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    ls224 = LakeShore224Interface(port='/dev/ttyUSB0')
    while True:
        temps = ls224.get_all_kelvin()
        if temps is None:
            logging.error("Failed to retrieve temperatures.")
            break
        else:
            logging.info("LS224 Temperatures (K): %s", temps)
        print("LS224 Temperatures (K):", temps)
        time.sleep(5)