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

    
    