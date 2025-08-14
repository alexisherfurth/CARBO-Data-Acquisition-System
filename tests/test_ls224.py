import sys
import os
import time
from lakeshore import Model224

my_instrument = Model224(com_port='/dev/ttyUSB0')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def main():
    # Adjust port as needed
    device = Model224(com_port='/dev/ttyUSB0')
    print("Querying device ID...")
    print(device.query("*IDN?"))  # Or the appropriate command for LS224

if __name__ == "__main__":
    main()