# Constants

# GPIO direction constants (referenced from MicroBlaze gpio.h)
# See https://github.com/Xilinx/PYNQ/blob/master/boards/sw_repo/pynqmb/src/gpio.h
GPIO_OUT = 0
GPIO_IN  = 1

class Status_LED():
    def __init__(self, parent_class, red_pin = 0, green_pin = 1):
        # 2-color status LED is on PMODB. Red pin is connected to
        # pin 0 and green pin is connected pin 1

        self.parent_class = parent_class
        self.enable = self.parent_class.status_led_enabled
        self.logger = self.parent_class.logger
        self.lock = self.parent_class.pmodB_lock
        self.inited = False

        if not self.enable:
            self.logger.info(f"Status LED not initialized")
            return

        if self._init_pin(green_pin) == 0:
            self.green_pin = green_pin

        if self._init_pin(red_pin) == 0:
            self.red_pin = red_pin

        self.inited = True

    def _init_pin(self, pin):
        # PMODs only have 1 PWM - PMODB PWM is being used by IR
        # transmitter

        # self.lock.acquire()
        # err = self.parent_class.mb_pmodb.init_pwm(pin)
        # self.lock.release()

        # if (err != 0):
        #     self.logger.error(
        #         f"init_pwm failed for pin {pin}, err: {err}")
        # else:
        #     self.logger.debug(
        #         f"init_pwm successful for pin {pin}")

        self.lock.acquire()
        err = self.parent_class.mb_pmodb.init_gpio(pin, GPIO_OUT)
        self.lock.release()

        if (err != 0):
            self.logger.error(
                f"init_gpio failed for pin {pin}, err: {err}")
            return -1
        else:
            self.logger.debug(
                f"init_gpio successful for pin {pin}")

        self.lock.acquire()
        err = self.parent_class.mb_pmodb.write_gpio(pin, 0)
        self.lock.release()

        if (err != 0):
            self.logger.error(
                f"write_gpio during LED init failed for pin {pin}, err: {err}")
            return -1
        else:
            self.logger.debug(
                f"write_gpio successful during LED init for pin {pin}")

        return 0

    def _set_pin(self, pin, val):
        # PMODs only have 1 PWM - PMODB PWM is being used by IR
        # transmitter

        # if duty_cycle != 0:
        #     self.lock.acquire()
        #     err = self.parent_class.mb_pmodb.start_pwm(pin, 500, duty_cycle)
        #     self.lock.release()

        #     if (err != 0):
        #         self.logger.error(
        #             f"start_pwm failed for pin {pin}, err: {err}")
        #     else:
        #         self.logger.debug(
        #             f"start_pwm successful for pin {pin}")

        # else:
        #     self.lock.acquire()
        #     err = self.parent_class.mb_pmodb.stop_pwm(pin)
        #     self.lock.release()

        #     if (err != 0):
        #         self.logger.error(
        #             f"stop_pwm failed for pin {pin}, err: {err}")
        #     else:
        #         self.logger.debug(
        #             f"stop_pwm successful for pin {pin}")

        self.lock.acquire()
        err = self.parent_class.mb_pmodb.write_gpio(pin, val)
        self.lock.release()

        if (err != 0):
            self.logger.error(
                f"write_gpio failed for pin {pin}, err: {err}")
        else:
            self.logger.debug(
                f"write_gpio successful for pin {pin}")

    def set_color(self, color):
        if not self.inited:
            return

        if color == "green":
            self._set_pin(self.green_pin, 1)
            self._set_pin(self.red_pin, 0)

        elif color == "red":
            self._set_pin(self.red_pin, 1)
            self._set_pin(self.green_pin, 0)

        elif color == "yellow":
            self._set_pin(self.green_pin, 1)
            self._set_pin(self.red_pin, 1)

        else:
            self.logger.error(
                f"Unknown color passed to set_color: {color}")
            
