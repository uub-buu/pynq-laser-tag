import time, datetime, threading, logging

from dc_motor import *
from ir_rx import *
from ir_tx import *
from status_led import *

# Constants

GAME_MODE_SUDDEN_DEATH  = 0
GAME_MODE_THREE_STRIKES = 1

class RC_Car:
    def __init__(
        self, mb_pmoda, mb_pmodb, mb_arduino, game_mode,
        weapons = True, status_led = True, log_level = logging.INFO):

        # MircoBlaze lib objects
        self.mb_pmoda = mb_pmoda
        self.mb_pmodb = mb_pmodb
        self.mb_arduino = mb_arduino

        self.status_led_enabled = status_led

        self.game_mode = game_mode
        self.strike_count = 0
        self.game_start_time = time.time()

        # Logging
        self.logger = logging.getLogger("PYNQ-Tag")
        self.logger.setLevel(log_level)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"PYNQ-Tag-{timestamp}.log"
        self.logfile_handler = logging.FileHandler(filename, mode="w")

        self.logfile_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"))
        self.logger.addHandler(self.logfile_handler)

        self.logger.info(f"Beginning program in mode {self.game_mode}")
        self.logger.debug(f"Logging initialized")

        # Overall "kill"/stop/lost event
        self.stop_event = threading.Event()
        self.stop_event.clear()

        # Motors
        self.logger.debug(f"Initializing motors")

        # Duty cycle for the initial/default speed
        self.init_speed = 75

        # Reduced speed for gradual turns (FL, FR, BL, BR)
        self.turn_speed = 30

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

        self.steer_thread = threading.Thread(
            target = self.steer_t, args = ())

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

        # Status LED
        #     Green - All systems go for launch! Still in play/winner
        #     Red - Lost
        if status_led:
            self.logger.debug(f"Initializing status LED")
        else:
            self.logger.debug(
                f"Skipping status LED initialization")

        self.status_led = Status_LED(parent_class = self)
        if status_led:
            self.logger.debug(f"Status LED initialized")

    def start(self):
        # Set the status LED to green (ready)
        self.status_led.set_color("green")

        self.steer_thread.start()

        self.logger.debug(f"Initialized steer_thread")

    def steer_t(self):
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
            # Stop the thread if we lost
            if self.stop_event.is_set():
                break

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

    # This blocks the main game process
    def wait_for_stop(self):
        while True:
            try:
                if not self.stop_event.is_set():
                    continue
                else:
                    return
            except KeyboardInterrupt:
                return

    def _stop(self):
        # Set the status LED to red (stop/lost)
        self.status_led.set_color("red")

        # De-initialize SPI
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

    def process_hit(self):
        # Update the strike count
        self.strike_count = self.strike_count + 1
        self.logger.debug(f"Strike count: {self.strike_count}")

        if self.game_mode == GAME_MODE_SUDDEN_DEATH:            
            self._stop()

        elif self.game_mode == GAME_MODE_THREE_STRIKES:
            if self.strike_count == 2:
                self.status_led.set_color("yellow")

            elif self.strike_count > 2:
                self._stop()

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
