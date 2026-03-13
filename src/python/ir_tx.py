import time, threading
class IR_Transmitter:
    def __init__(self, pmodb, pmodb_lock, logger, weapons, pin = 7):
        # IR transmitter "laser" is on PMODB and connected to
        # pin 7

        self.logger = logger
        self.enable = weapons
        self.mb_pmodb = pmodb
        self.pmodb_lock = pmodb_lock
        if not self.enable:
            self.logger.info(f"Laser not initialized")
            return

        err = self.mb_pmodb.init_pwm(pin)
        if (err != 0):
            self.logger.error(
                f"init_pwm failed for pin {pin}, err: {err}")
        else:
            self.logger.debug(
                f"init_pwm successful for pin {pin}")

        self.pwm_period_usec = 26 # 26 usec is about 38.4 KHz
        self.pwm_duty_cycle = 50
        self.pwm_pin = pin
        self.laser_pulse_duration_msec = 250 # 250 msec pulse

        self.shoot_event = threading.Event()
        self.shoot_thread = threading.Thread(
            target = self.shoot_t,
            args = (self.pmodB_lock, self.shoot_event))

        self.shoot_thread.start()

        self.logger.info(f"Initialized laser shoot thread")
        self.logger.debug(f"Laser signal pin: {self.pwm_pin}")
        self.logger.debug(
            f"Laser pulse duration: {self.laser_pulse_duration_msec} milliseconds")

    def shoot_t(self, lock, shoot_event):
        while True:
            # Wait until shoot_event is set
            if not shoot_event.is_set():
                continue

            self._shoot(lock)
            shoot_event.clear()

    def _shoot(self, lock):
        if not self.enable:
            self.logger.debug(f"Laser could not be shot - not initialized!")
            return

        # Shoot a quarter second pulse "laser"
        lock.acquire()
        err = self.mb_pmodb.start_pwm(
            self.pwm_pin,
            self.pwm_period_usec,
            self.pwm_duty_cycle)
        lock.release()

        if (err != 0):
            self.logger.error(
                f"start_pwm failed for pin {self.pwm_pin}, err: {err}")
        else:
            self.logger.debug(
                f"start_pwm successful for pin {self.pwm_pin}")

        time.sleep(self.laser_pulse_duration_msec / 1000)

        lock.acquire()
        err = self.mb_pmodb.stop_pwm(self.pwm_pin)
        lock.release()

        if (err != 0):
            self.logger.error(
                f"stop_pwm failed for pin {self.pwm_pin}, err: {err}")
        else:
            self.logger.debug(
                f"stop_pwm successful for pin {self.pwm_pin}")

        self.logger.info(f"Laser shot!")
