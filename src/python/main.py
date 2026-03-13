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

# Constants

# GPIO direction constants (referenced from MicroBlaze gpio.h)
# See https://github.com/Xilinx/PYNQ/blob/master/boards/sw_repo/pynqmb/src/gpio.h
GPIO_OUT = 0
GPIO_IN  = 1

# Following constants were referenced from AdaFruit motor shield v1 library
# See https://github.com/adafruit/Adafruit-Motor-Shield-library

# Constants that the user passes in to the motor calls
FORWARD  = 1
BACKWARD = 2
BRAKE    = 3
RELEASE  = 4

motor_dir_map = [
    "",
    "forward",
    "backward",
    "brake",
    "release",
]

# Constants to denote motor numbers connected to the shield
MOTOR_FL = 1 # Front left - M1
MOTOR_BL = 2 # Back left - M2
MOTOR_BR = 3 # Back right - M3
MOTOR_FR = 4 # Front right - M4

# Constants that encode the joystick D-pad user input
# This corresponds to map_to_direction() in joystick_controller.ino
DPAD_NEUTRAL        = 0
DPAD_LEFT           = 1
DPAD_RIGHT          = 2
DPAD_FORWARD        = 3
DPAD_BACKWARD       = 4
DPAD_FORWARD_LEFT   = 5
DPAD_FORWARD_RIGHT  = 6
DPAD_BACKWARD_LEFT  = 7
DPAD_BACKWARD_RIGHT = 8

dpad_dir_map = [
    "neutral",
    "left",
    "right",
    "forward",
    "backward",
    "forward_left",
    "forward_right",
    "backward_left",
    "backward_right",
]

class DCMotor:
    def __init__(self, motornum, init_speed, logger):
        self.motornum = motornum
        self.speed = init_speed
        self.logger = logger

        # Let the first .run() through
        self.direction = -1

        self.logger.debug(f"DCMotor_init called for motor {motornum}")

        err = mb_arduino.DCMotor_init(motornum, init_speed)
        if (err != 0):
            self.logger.error(
                f"DCMotor_init for motor {motornum} failed, err: {err}")
            return
        else:
            self.logger.debug(
                f"DCMotor_init for motor {motornum} successful")

        #self.set_speed_event = threading.Event()
        #self.set_speed_thread = threading.Thread(
        #    target = self.set_speed_t,
        #    args = ())

        #self.set_speed_thread.start()

    #def set_speed_t(self):
    #    print(f"Set speed thread for motor {self.motornum} started")

    def run(self, direction):
        # Short circuit if there's no change, save ourselves a
        # MicroBlaze RPC
        if (direction != self.direction):
            self.logger.debug(
                f"DCMotor_run called for motor {self.motornum}, direction {motor_dir_map[direction]}")

            err = mb_arduino.DCMotor_run(self.motornum, direction)

            if (err != 0):
                self.logger.error(
                    f"DCMotor_run for motor {self.motornum} failed, err: {err}")
                return
            else:
                self.logger.debug(
                    f"DCMotor_run for motor {self.motornum} successful")

    def set_speed(self, speed):
        # Short circuit if there's no change, save ourselves a
        # MicroBlaze RPC
        if (speed != self.speed):
            self.logger.debug(
                f"DCMotor_setSpeed called for motor {self.motornum}, speed {speed}")

            err = mb_arduino.DCMotor_setSpeed(self.motornum, speed)
            if (err != 0):
                self.logger.error(
                    f"DCMotor_setSpeed for motor {self.motornum} failed, err: {err}")
                return
            else:
                self.logger.debug(
                    f"DCMotor_setSpeed for motor {self.motornum} successful")


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