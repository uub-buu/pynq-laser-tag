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
        self.red_pin = -1
        self.green_pin = -1

        if not self.enable:
            self.logger.info(f"Status LED not initialized")
            return

        if self._init_pin(green_pin) == 0:
            self.green_pin = green_pin

        if self._init_pin(red_pin) == 0:
            self.red_pin = red_pin

    def _init_pin(self, pin):
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

    def set_color(self, color = "green"):
        if color == "green" and self.green_pin != -1:
            self.lock.acquire()
            err = self.parent_class.mb_pmodb.write_gpio(self.green_pin, 1)
            self.lock.release()

            if (err != 0):
                self.logger.error(
                    f"write_gpio failed for pin {self.green_pin}, err: {err}")
            else:
                self.logger.debug(
                    f"write_gpio successful for pin {self.green_pin}")

        elif color == "red" and self.red_pin != -1:
            self.lock.acquire()
            err = self.parent_class.mb_pmodb.write_gpio(self.red_pin, 1)
            self.lock.release()

            if (err != 0):
                self.logger.error(
                    f"write_gpio failed for pin {self.red_pin}, err: {err}")
            else:
                self.logger.debug(
                    f"write_gpio successful for pin {self.red_pin}")

        else:
            self.logger.error(
                f"Unknown color passed to set_color: err: {color}")
            
