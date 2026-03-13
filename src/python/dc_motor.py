import logging

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
    def __init__(self, motornum, init_speed, logger, mb_arduino):
        self.motornum = motornum
        self.speed = init_speed
        self.logger = logger
        self.mb_arduino = mb_arduino

        # Let the first .run() through
        self.direction = -1

        self.logger.debug(f"DCMotor_init called for motor {motornum}")

        err = self.mb_arduino.DCMotor_init(motornum, init_speed)
        if (err != 0):
            self.logger.error(
                f"DCMotor_init for motor {motornum} failed, err: {err}")
            return
        else:
            self.logger.debug(
                f"DCMotor_init for motor {motornum} successful")

    def run(self, direction):
        self.logger.debug(
            f"DCMotor_run called for motor {self.motornum}, direction {motor_dir_map[direction]}")
        self.logger.debug(
            f"Motor {self.motornum} current direction: {motor_dir_map[self.direction]}")

        # Short circuit if there's no change, save ourselves a
        # MicroBlaze RPC
        if (direction != self.direction):
            err = self.mb_arduino.DCMotor_run(self.motornum, direction)

            if (err != 0):
                self.logger.error(
                    f"DCMotor_run for motor {self.motornum} failed, err: {err}")
                return
            else:
                self.logger.debug(
                    f"DCMotor_run for motor {self.motornum} successful")

                # Update the direction in class member
                self.direction = direction

    def set_speed(self, speed):
        self.logger.debug(
            f"DCMotor_setSpeed called for motor {self.motornum}, speed {speed}")
        self.logger.debug(
            f"Motor {self.motornum} current speed: {self.speed}")

        # Short circuit if there's no change, save ourselves a
        # MicroBlaze RPC
        if (speed != self.speed):
            err = self.mb_arduino.DCMotor_setSpeed(self.motornum, speed)
            if (err != 0):
                self.logger.error(
                    f"DCMotor_setSpeed for motor {self.motornum} failed, err: {err}")
                return
            else:
                self.logger.debug(
                    f"DCMotor_setSpeed for motor {self.motornum} successful")

                # Update the speed in class member
                self.speed = speed
