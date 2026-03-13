import time, threading, logging
from dc_motor import *
class IR_Receiver():
    def __init__(self, pmodb,pmodb_lock, logger, weapons, pin = 3):
        # IR receiver is on PMODB and connected to pin 3
        self.enable = weapons
        self.logger = logger
        self.mb_pmodb = pmodb
        self,pmodb_lock
        if not self.enable:
            self.logger.info(f"IR receiver not initialized")
            return

        err = self.mb_pmod.init_gpio(pin, GPIO_IN)
        if (err != 0):
            self.logger.error(
                f"init_gpio failed for pin {pin}, err: {err}")
        else:
            self.logger.debug(
                f"init_gpio successful for pin {pin}")

        self.ir_pin = pin

        # Start a process which indicates a hit
        self.ir_rx_thread = threading.Thread(
            target = self.notify_hit_t,
            args = (self, pmodb_lock, ))

        self.ir_rx_thread.start()

        self.logger.info(f"Initialized IR Receiver thread")
        self.logger.debug(f"IR receiver signal pin: {self.ir_pin}")

    def notify_hit_t(self, car, lock):
        if not self.enable:
            return

        lock.acquire()
        prev_read = self.mb_pmod.read_gpio(self.ir_pin)
        lock.release()
        while True:
            lock.acquire()
            curr_read = self.mb_pmod.read_gpio(self.ir_pin)
            lock.release()
            if curr_read == 0 and curr_read != prev_read:
                self.logger.info("Hit!")
                car.stop()
            prev_read = curr_read
            time.sleep(0.01)
