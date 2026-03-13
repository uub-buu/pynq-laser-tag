class RC_Car:
    def __init__(self, weapons = True, log_level = logging.INFO):
        # Logging
        self.logger = logging.getLogger("PYNQ-Tag")
        self.logger.setLevel(log_level)
        self.logfile_handler = logging.FileHandler(
            "PYNQ-Tag.log", mode="w")

        self.logfile_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"))
        self.logger.addHandler(self.logfile_handler)

        self.logger.info(f"Beginning program...")
        self.logger.debug(f"Logging initialized")

        # Motors
        self.logger.debug(f"Initializing motors")

        # Duty cycle for the initial/default speed
        self.init_speed = 40

        # Reduced speed for gradual turns (FL, FR, BL, BR)
        self.turn_speed = 20

        self.motor_fl = DCMotor(MOTOR_FL, self.init_speed, self.logger)
        self.motor_fr = DCMotor(MOTOR_FR, self.init_speed, self.logger)
        self.motor_bl = DCMotor(MOTOR_BL, self.init_speed, self.logger)
        self.motor_br = DCMotor(MOTOR_BR, self.init_speed, self.logger)
        self.motors = [
            self.motor_fl,
            self.motor_bl,
            self.motor_fr,
            self.motor_br,
        ]
        self.l_motors = [self.motor_fl, self.motor_bl]
        self.r_motors = [self.motor_fr, self.motor_br]
        self.logger.debug(f"Motors initialized")

        # Weapons
        self.weapons = weapons
        if weapons:
            self.logger.debug(
                f"Initializing IR transmitter and receiver")
        else:
            self.logger.debug(
                f"Skipping IR transmitter and receiver initialization")

        self.pmodB_lock = threading.Lock()
        self.ir_transmitter = self.IR_Transmitter(parent_class = self)
        self.ir_receiver = self.IR_Receiver(parent_class = self)
        if weapons:
            self.logger.debug(f"IR transmitter and receiver initialized")

    def start(self):
        # Joystick link
        err = mb_pmoda.spi_init()
        if (err != 0):
            self.logger.error(f"spi_init failed, err: {err}")
            return
        else:
            self.logger.debug(f"spi_init successful")

    def fire_laser(self):
        if self.weapons:
            self.ir_transmitter.shoot_event.set()

    def stop(self):
        self.logger.info(f"Stopping program...")
        self.logfile_handler.close()
        mb_pmoda.spi_deinit()
        for motor in self.motors:
            motor.run(RELEASE)

    def move(self, cmd):
        #global dpad_dir_map
        self.logger.debug(f"Received command: {dpad_dir_map[cmd]}")
        if (cmd == DPAD_FORWARD):
            for motor in self.motors:
                motor.run(FORWARD)
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_BACKWARD):
            for motor in self.motors:
                motor.run(BACKWARD)
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_LEFT):
            for motor in self.l_motors:
                motor.run(BACKWARD)
                motor.set_speed(self.init_speed)
            for motor in self.r_motors:
                motor.run(FORWARD)
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_RIGHT):
            for motor in self.l_motors:
                motor.run(FORWARD)
                motor.set_speed(self.init_speed)
            for motor in self.r_motors:
                motor.run(BACKWARD)
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_FORWARD_LEFT):
            for motor in self.l_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.r_motors:
                motor.set_speed(self.init_speed)
            for motor in self.motors:
                motor.run(FORWARD)

        elif (cmd == DPAD_FORWARD_RIGHT):
            for motor in self.r_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.l_motors:
                motor.set_speed(self.init_speed)
            for motor in self.motors:
                motor.run(FORWARD)

        elif (cmd == DPAD_BACKWARD_LEFT):
            for motor in self.l_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.r_motors:
                motor.set_speed(self.init_speed)
            for motor in self.motors:
                motor.run(BACKWARD)

        elif (cmd == DPAD_BACKWARD_RIGHT):
            for motor in self.r_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.l_motors:
                motor.set_speed(self.init_speed)
            for motor in self.motors:
                motor.run(BACKWARD)

        elif (cmd == DPAD_NEUTRAL):
            for motor in self.motors:
                motor.run(RELEASE)

    class IR_Transmitter:
        def __init__(self, parent_class, pin = 7):
            # IR transmitter "laser" is on PMODB and connected to
            # pin 7

            self.logger = parent_class.logger
            self.enable = parent_class.weapons
            if not self.enable:
                self.logger.info(f"Laser not initialized")
                return

            err = mb_pmodb.init_pwm(pin)
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
                args = (parent_class.pmodB_lock, self.shoot_event))

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
            err = mb_pmodb.start_pwm(
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
            err = mb_pmodb.stop_pwm(self.pwm_pin)
            lock.release()

            if (err != 0):
                self.logger.error(
                    f"stop_pwm failed for pin {self.pwm_pin}, err: {err}")
            else:
                self.logger.debug(
                    f"stop_pwm successful for pin {self.pwm_pin}")

            self.logger.info(f"Laser shot!")

    class IR_Receiver():
        def __init__(self, parent_class, pin = 3):
            # IR receiver is on PMODB and connected to pin 3
            self.enable = parent_class.weapons
            self.logger = parent_class.logger
            if not self.enable:
                self.logger.info(f"IR receiver not initialized")
                return

            err = mb_pmodb.init_gpio(pin, GPIO_IN)
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
                args = (parent_class, parent_class.pmodB_lock, ))

            self.ir_rx_thread.start()

            self.logger.info(f"Initialized IR Receiver thread")
            self.logger.debug(f"IR receiver signal pin: {self.ir_pin}")

        def notify_hit_t(self, car, lock):
            if not self.enable:
                return

            lock.acquire()
            prev_read = mb_pmodb.read_gpio(self.ir_pin)
            lock.release()
            while True:
                lock.acquire()
                curr_read = mb_pmodb.read_gpio(self.ir_pin)
                lock.release()
                if curr_read == 0 and curr_read != prev_read:
                    self.logger.info("Hit!")
                    car.stop()
                prev_read = curr_read
                time.sleep(0.01)
