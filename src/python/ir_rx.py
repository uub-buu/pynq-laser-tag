import time, threading

# Constants

# GPIO direction constants (referenced from MicroBlaze gpio.h)
# See https://github.com/Xilinx/PYNQ/blob/master/boards/sw_repo/pynqmb/src/gpio.h
GPIO_OUT = 0
GPIO_IN  = 1

class IR_Receiver():
    def __init__(self, parent_class, pin = 3):
        # IR receiver is on PMODB and connected to pin 3

        self.parent_class = parent_class
        self.enable = self.parent_class.weapons
        self.logger = self.parent_class.logger
        self.lock = self.parent_class.pmodB_lock

        if not self.enable:
            self.logger.info(f"IR receiver not initialized")
            return

        err = self.parent_class.mb_pmodb.init_gpio(pin, GPIO_IN)
        if (err != 0):
            self.logger.error(
                f"init_gpio failed for pin {pin}, err: {err}")
        else:
            self.logger.debug(
                f"init_gpio successful for pin {pin}")

        self.ir_pin = pin

        # Start a process which indicates a hit
        self.ir_rx_thread = threading.Thread(target = self.notify_hit_t, args = ())

        self.ir_rx_thread.start()

        self.logger.debug(f"Initialized IR Receiver thread")
        self.logger.debug(f"IR receiver signal pin: {self.ir_pin}")

    def notify_hit_t(self):
        if not self.enable:
            return

        self.lock.acquire()
        prev_read = self.parent_class.mb_pmodb.read_gpio(self.ir_pin)
        self.lock.release()

        while True:
            self.lock.acquire()
            curr_read = self.parent_class.mb_pmodb.read_gpio(self.ir_pin)
            self.lock.release()

            if curr_read == 0 and curr_read != prev_read:
                self.logger.info("Hit!")
                self.parent_class.stop()
                break

            prev_read = curr_read
            time.sleep(0.01)
