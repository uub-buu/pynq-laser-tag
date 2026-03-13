import datetime, threading, logging

from dc_motor import *
from ir_rx import *
from ir_tx import *

class RC_Car:
    def __init__(
        self, mb_pmoda, mb_pmodb, mb_arduino,
        weapons = True, log_level = logging.INFO):

        # MircoBlaze lib objects
        self.mb_pmoda = mb_pmoda
        self.mb_pmodb = mb_pmodb
        self.mb_arduino = mb_arduino

        # Logging
        self.logger = logging.getLogger("PYNQ-Tag")
        self.logger.setLevel(log_level)
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        filename = f"PYNQ-Tag-{timestamp}.log"
        self.logfile_handler = logging.FileHandler(filename, mode="w")

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

        self.motor_fl = DCMotor(MOTOR_FL, self.init_speed, self.logger, self.mb_arduino)
        self.motor_fr = DCMotor(MOTOR_FR, self.init_speed, self.logger, self.mb_arduino)
        self.motor_bl = DCMotor(MOTOR_BL, self.init_speed, self.logger, self.mb_arduino)
        self.motor_br = DCMotor(MOTOR_BR, self.init_speed, self.logger, self.mb_arduino)
        self.motors = [
            self.motor_fl,
            self.motor_bl,
            self.motor_fr,
            self.motor_br,
        ]
        self.l_motors = [self.motor_fl, self.motor_bl]
        self.r_motors = [self.motor_fr, self.motor_br]
        self.logger.debug(f"Motors initialized")

        # SPI (joystick link)
        err = self.mb_pmoda.spi_init()
        if (err != 0):
            self.logger.error(f"spi_init failed, err: {err}")
            return
        else:
            self.logger.debug(f"spi_init successful")

        self.dpad_listener_thread = threading.Thread(
            target = self.dpad_listener_t, args = ())

        # Weapons
        self.weapons = weapons
        if weapons:
            self.logger.debug(
                f"Initializing IR transmitter and receiver")
        else:
            self.logger.debug(
                f"Skipping IR transmitter and receiver initialization")

        self.pmodB_lock = threading.Lock()
        self.ir_transmitter = IR_Transmitter(parent_class = self)
        self.ir_receiver = IR_Receiver(parent_class = self)
        if weapons:
            self.logger.debug(f"IR transmitter and receiver initialized")

    def start(self):
        self.dpad_listener_thread.start()

        self.logger.debug(
            f"Initialized listener thread for getting DPAD directions received over BT by ESP32")

    def dpad_listener_t(self):
        # SPI helper functions
        def get_laser_state(data_byte):
            return ((data_byte >> 7) & 1)

        def get_motor_cmd(data_byte):
            return (data_byte & 0xF)

        # NOTE: Noticed some stale data in SPI sometimes where the last
        #       command comes up at the very beginning. Ignore this first
        #       read and always start from NEUTRAL.
        prev_data = self.mb_pmoda.spi_read_data()
        prev_dpad_dir = DPAD_NEUTRAL
        self.steer(prev_dpad_dir)

        while True:
            data = self.mb_pmoda.spi_read_data()
            laser = get_laser_state(data)
            dpad_dir = get_motor_cmd(data)

            if dpad_dir >= DPAD_NEUTRAL and dpad_dir <= DPAD_BACKWARD_RIGHT:
                if dpad_dir != prev_dpad_dir:
                    self.steer(dpad_dir)
                    prev_dpad_dir = dpad_dir

            if laser == 1:
                self.fire_laser()

            time.sleep(0.01)

    def fire_laser(self):
        if self.weapons:
            self.ir_transmitter.shoot_event.set()

    def wait_for_stop(self):
        self.stop_event = threading.Event()
        self.stop_event.clear()

        while True:
            try:
                if not self.stop_event.is_set():
                    continue
            except KeyboardInterrupt:
                return
        
    def stop(self):
        # De-initialize
        self.logger.debug(f"De-initializing SPI")
        self.mb_pmoda.spi_deinit()

        # Stop the motors
        self.logger.debug(f"Releasing the motors")
        for motor in self.motors:
            motor.run(RELEASE)

        # Close the logger
        self.logger.info(f"Stopping program...")
        self.logfile_handler.close()

        # Return to the main process
        try:
            self.stop_event.set()
        except:
            exit(1)

    def steer(self, cmd):
        self.logger.debug(f"Received command: {dpad_dir_map[cmd]}")

        # Calling motor.run() in a loop introduced significant
        # delays - falling back to un-rolled loops
        if (cmd == DPAD_FORWARD):
            self.motor_fl.run(FORWARD)
            self.motor_fr.run(FORWARD)
            self.motor_bl.run(FORWARD)
            self.motor_br.run(FORWARD)

            for motor in self.motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_BACKWARD):
            self.motor_bl.run(BACKWARD)
            self.motor_br.run(BACKWARD)
            self.motor_fl.run(BACKWARD)
            self.motor_fr.run(BACKWARD)

            for motor in self.motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_LEFT):
            self.motor_fl.run(BACKWARD)
            self.motor_bl.run(BACKWARD)
            self.motor_fr.run(FORWARD)
            self.motor_br.run(FORWARD)

            for motor in self.motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_RIGHT):
            self.motor_fr.run(BACKWARD)
            self.motor_br.run(BACKWARD)
            self.motor_fl.run(FORWARD)
            self.motor_bl.run(FORWARD)

            for motor in self.motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_FORWARD_LEFT):
            self.motor_fl.run(FORWARD)
            self.motor_fr.run(FORWARD)
            self.motor_bl.run(FORWARD)
            self.motor_br.run(FORWARD)

            for motor in self.l_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.r_motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_FORWARD_RIGHT):
            self.motor_fl.run(FORWARD)
            self.motor_fr.run(FORWARD)
            self.motor_bl.run(FORWARD)
            self.motor_br.run(FORWARD)

            for motor in self.r_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.l_motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_BACKWARD_LEFT):
            self.motor_bl.run(BACKWARD)
            self.motor_br.run(BACKWARD)
            self.motor_fl.run(BACKWARD)
            self.motor_fr.run(BACKWARD)

            for motor in self.l_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.r_motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_BACKWARD_RIGHT):
            self.motor_bl.run(BACKWARD)
            self.motor_br.run(BACKWARD)
            self.motor_fl.run(BACKWARD)
            self.motor_fr.run(BACKWARD)

            for motor in self.r_motors:
                motor.set_speed(self.turn_speed)
            for motor in self.l_motors:
                motor.set_speed(self.init_speed)

        elif (cmd == DPAD_NEUTRAL):
            for motor in self.motors:
                motor.run(RELEASE)
