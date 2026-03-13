import os, time, threading, multiprocessing, logging

from pynq.overlays.base import BaseOverlay
from pynq.lib.pynqmicroblaze.rpc import MicroblazeRPC
from pmoda import source_pmoda
from pmodb import source_pmodb
from pmod_arduino import source_arduino




# Build/load MicroBlaze to IOP PMODA, PMODB and ARDUINO

# SPI helper functions
def get_laser_state(data_byte):
    return ((data_byte >> 7) & 1)

def get_motor_cmd(data_byte):
    return (data_byte & 0xF)

# Main entry point
def run():
    base = BaseOverlay("base.bit")
    mb_arduino = MicroblazeRPC(base.iop_arduino, source_arduino)
    mb_pmoda = MicroblazeRPC(base.iop_pmoda, source_pmoda)
    mb_pmodb = MicroblazeRPC(base.iop_pmodb, source_pmodb)
    # Game entry point
    car = RC_Car(log_level = logging.INFO)

    car.start()

    # NOTE: Noticed some stale data in SPI sometimes where the
    #       last command comes up at the very beginning. Ignore
    #       this first read and always start from NEUTRAL.
    prev_data = mb_pmoda.spi_read_data()
    prev_dpad_dir = DPAD_NEUTRAL
    car.move(DPAD_NEUTRAL)

    while True:
        data = mb_pmoda.spi_read_data()
        laser = get_laser_state(data)
        dpad_dir = get_motor_cmd(data)

        if dpad_dir >= DPAD_NEUTRAL and dpad_dir <= DPAD_BACKWARD_RIGHT:
            if dpad_dir != prev_dpad_dir:
                car.move(dpad_dir)
                prev_dpad_dir = dpad_dir

        if laser == 1:
            car.fire_laser()

        time.sleep(0.01)

if __name__ == "__main__":
    print(f"Booting application...")
    run()