import os, time, threading, multiprocessing, logging

from pynq.overlays.base import BaseOverlay
from pynq.lib.pynqmicroblaze.rpc import MicroblazeRPC

base = BaseOverlay("base.bit")

source_pmoda = r'''

#include <stdint.h>
#include <stdbool.h>
#include "pyprintf.h"
#include "spi.h"

#define DEBUG_MODE      0

#define SUCCESS         0
#define ERR_INVALID    -1
#define ERR_NOTREADY   -2
#define ERR_GENERIC    -3

static char rx_buff;
const char  tx_buff = '\0';
static bool spi_inited = false;

unsigned int DATA_BYTE_SIZE = 1;
unsigned int SCLK_PIN = 0;
unsigned int MISO_PIN = 1;
unsigned int MOSI_PIN = 2;
unsigned int CS_PIN = 3;

spi spi_dev;

// Initialize SPI device (PYNQ will be master)
int spi_init
(
    void
)
{
    if (spi_inited)
    {
        return SUCCESS;
    }

    spi_dev = spi_open(SCLK_PIN, MISO_PIN, MOSI_PIN, CS_PIN);

    // spi_open returns -1 in case of an error
    if (spi_dev < 0)
    {
        #if DEBUG_MODE
        pyprintf("spi_open failed, err %d\n", spi_dev);
        #endif

        return ERR_GENERIC;
    }

    spi_configure(spi_dev, 0, 0); // CPOL = 0, CPHA = 0 (mode 0)

    #if DEBUG_MODE
    pyprintf("spi_open successful");
    #endif

    spi_inited = true;

    return SUCCESS;
}

// Read data over SPI
unsigned int spi_read_data
(
    void
)
{
    if (!spi_inited)
    {
        return ERR_NOTREADY;
    }

    spi_transfer(spi_dev, &tx_buff, &rx_buff, DATA_BYTE_SIZE);
    return (unsigned int)rx_buff;
}

// De-initialize SPI device
int spi_deinit
(
    void
)
{
    if (!spi_inited)
    {
        return SUCCESS;
    }

    spi_close(spi_dev);

    #if DEBUG_MODE
    pyprintf("spi_close done");
    #endif

    spi_inited = false;

    return SUCCESS;
}
'''

source_pmodb = r'''

#include <stdint.h>
#include <stdbool.h>
#include "pyprintf.h"
#include "xio_switch.h"
#include "gpio.h"
#include "timer.h"

#define DEBUG_MODE      0

#define SUCCESS         0
#define ERR_INVALID    -1
#define ERR_NOTREADY   -2

#define NUM_PINS        8

#define TIMER_FREQ_MHZ  100

typedef struct
{
    bool inited;
    gpio gpio_dev;

} gpio_handle_t;

typedef struct
{
    bool  inited;
    timer timer_dev;

} timer_handle_t;

gpio_handle_t  gpio_handles[NUM_PINS];
timer_handle_t timer_handles[NUM_PINS];

// Initialization function to cache a GPIO handle and set the
// direction; this may be more efficient for repeated IO operations

int init_gpio
(
    unsigned int pin,
    unsigned int direction
)
{
    #if DEBUG_MODE
    pyprintf("init_gpio called for pin %u\n", pin);
    #endif

    if (pin >= NUM_PINS)
    {
        return ERR_INVALID;
    }

    if ((direction != GPIO_IN) && (direction != GPIO_OUT))
    {
        return ERR_INVALID;
    }

    gpio_handles[pin].gpio_dev = gpio_open(pin);
    gpio_set_direction(gpio_handles[pin].gpio_dev, direction);
    gpio_handles[pin].inited = true;

    #if DEBUG_MODE
    pyprintf("init_gpio done for pin %u\n", pin);
    #endif

    return SUCCESS;
}

// Function to write to a PMOD pin

int write_gpio
(
    unsigned int pin,
    unsigned int val
)
{
    if (pin >= NUM_PINS)
    {
        return ERR_INVALID;
    }

    if (!gpio_handles[pin].inited)
    {
        return ERR_NOTREADY;
    }

    if (val > 1) {
        // Technically, an error, but just limit the user input to 1
        val = 1;
    }

    gpio_write(gpio_handles[pin].gpio_dev, val);

    return SUCCESS;
}

// Function to read a PMOD pin

int read_gpio
(
    unsigned int pin
)
{
    if (pin >= NUM_PINS)
    {
        return ERR_INVALID;
    }

    if (!gpio_handles[pin].inited)
    {
        return ERR_NOTREADY;
    }

    return gpio_read(gpio_handles[pin].gpio_dev);
}

// Initialization function to cache a timer handle and set the
// direction; this may be more efficient for repeated IO operations

int init_pwm
(
    unsigned int pin
)
{
    #if DEBUG_MODE
    pyprintf("init_pwm called for pin %u\n", pin);
    #endif

    if (pin >= NUM_PINS)
    {
        return ERR_INVALID;
    }

    timer_handles[pin].timer_dev = timer_open_device(0);
    init_io_switch();
    set_pin(pin, PWM0);
    timer_handles[pin].inited = true;

    #if DEBUG_MODE
    pyprintf("init_pwm done for pin %u\n", pin);
    #endif

    return SUCCESS;
}

int start_pwm
(
    unsigned int pin,
    unsigned int period_usec,
    unsigned int duty_cycle
)
{
    #if DEBUG_MODE
    pyprintf("start_pwm called for pin %u\n", pin);
    #endif

    if (pin >= NUM_PINS)
    {
        return ERR_INVALID;
    }

    if ((period_usec == 0) || (period_usec >= 65536) ||
        (duty_cycle  == 0) || (duty_cycle >= 100))
    {
        return ERR_INVALID;
    }

    if (!timer_handles[pin].inited)
    {
        return ERR_NOTREADY;
    }

    // Convert the period input in microseconds to AXI Timer clock ticks
    unsigned int period = period_usec * TIMER_FREQ_MHZ;

    // Calculate the pulse from duty_cycle
    unsigned int pulse = duty_cycle * period / 100;

    timer_pwm_generate(timer_handles[pin].timer_dev, period, pulse);

    #if DEBUG_MODE
    pyprintf("start_pwm done for pin %u\n", pin);
    #endif

    return SUCCESS;
}

int stop_pwm
(
    unsigned int pin
)
{
    #if DEBUG_MODE
    pyprintf("stop_pwm called for pin %u\n", pin);
    #endif

    if (pin >= NUM_PINS) {
        return ERR_INVALID;
    }

    timer_pwm_stop(timer_handles[pin].timer_dev);

    #if DEBUG_MODE
    pyprintf("stop_pwm done for pin %u\n", pin);
    #endif

    return SUCCESS;
}
'''

source_arduino = r'''
#include <stdint.h>
#include <stdbool.h>
#include <xparameters.h>
#include "pyprintf.h"
#include "xio_switch.h"
#include "gpio.h"
#include "timer.h"

#define DEBUG_MODE      0

#define ENABLE_PWM      1

#define SUCCESS         0
#define ERR_INVALID    -1
#define ERR_NOTREADY   -2

#define _BV(bit)          (1 << (bit))

#define NUM_MOTORS        4

// Arduino pin numbers for interface to 74HC595N latch
#define MOTOR_PIN_LATCH   12
#define MOTOR_PIN_CLK     4
#define MOTOR_PIN_ENABLE  7
#define MOTOR_PIN_DATA    8

// Arduino pin numbers for motor PWM control
#define MOTOR1_PWM_PIN    11
#define MOTOR2_PWM_PIN    3
#define MOTOR3_PWM_PIN    6
#define MOTOR4_PWM_PIN    5

// Bit positions in the 74HC595N shift register output
#define MOTOR1_A          2
#define MOTOR1_B          3
#define MOTOR2_A          1
#define MOTOR2_B          4
#define MOTOR4_A          0
#define MOTOR4_B          6
#define MOTOR3_A          5
#define MOTOR3_B          7

// Constants that the user passes in to the motor calls
#define FORWARD           1
#define BACKWARD          2
#define BRAKE             3
#define RELEASE           4

#define TIMER_FREQ_MHZ    100
#define PWM_FREQ_KHZ      2
#define PWM_PERIOD_TICKS  ((1000 / PWM_FREQ_KHZ) * TIMER_FREQ_MHZ)

static uint8_t latch_state;
static bool    motor_controller_enabled = false;

gpio motor_pin_latch;
gpio motor_pin_enable;
gpio motor_pin_data;
gpio motor_pin_clk;

typedef struct
{
    bool  inited;
    timer timer_dev;

} timer_handle_t;

timer_handle_t timer_handles[NUM_MOTORS];

static void MotorController_latch_tx
(
    void
)
{
    uint8_t i;

    gpio_write(motor_pin_latch, 0);
    gpio_write(motor_pin_data, 0);

    for (i = 0; i < 8; i++)
    {
        gpio_write(motor_pin_clk, 0);

        if (latch_state & _BV(7-i))
        {
            gpio_write(motor_pin_data, 1);
        }
        else
        {
            gpio_write(motor_pin_data, 0);
        }

        gpio_write(motor_pin_clk, 1);
    }

    gpio_write(motor_pin_latch, 1);
}

static void MotorController_enable
(
    void
)
{
    // Only need to enable the motor controller once
    if (motor_controller_enabled)
    {
        return;
    }

    init_io_switch();
    motor_pin_latch  = gpio_open(MOTOR_PIN_LATCH);
    motor_pin_enable = gpio_open(MOTOR_PIN_ENABLE);
    motor_pin_data   = gpio_open(MOTOR_PIN_DATA);
    motor_pin_clk    = gpio_open(MOTOR_PIN_CLK);

    gpio_set_direction(motor_pin_latch, GPIO_OUT);
    gpio_set_direction(motor_pin_enable, GPIO_OUT);
    gpio_set_direction(motor_pin_data, GPIO_OUT);
    gpio_set_direction(motor_pin_clk, GPIO_OUT);

    latch_state = 0;

    MotorController_latch_tx();  // "reset"

    gpio_write(motor_pin_enable, 0);

    motor_controller_enabled = true;
}

// num: Motor number
// speed: 1-100 number
int DCMotor_init
(
    unsigned int motornum,
    unsigned int init_speed
)
{
    unsigned int num, pulse;

    if ((motornum   == 0) || (motornum   > 4) ||
        (init_speed == 0) || (init_speed > 100))
    {
        return ERR_INVALID;
    }

    MotorController_enable();

    // Calculate the pulse from initial speed input (duty cycle)
    pulse = init_speed * PWM_PERIOD_TICKS / 100;

    num = motornum - 1;

    #if DEBUG_MODE
    pyprintf("DCMotor_init called for motor %u\n", motornum);
    #endif

    switch (motornum)
    {
        case 1:
            latch_state &= ~_BV(MOTOR1_A) & ~_BV(MOTOR1_B);
            MotorController_latch_tx();

            #if ENABLE_PWM
            timer_handles[num].timer_dev =
                   timer_open_device(XPAR_IO_SWITCH_0_TIMER0_BASEADDR);
            set_pin(MOTOR1_PWM_PIN, PWM0);
            timer_handles[num].inited = true;
            timer_pwm_generate(
                timer_handles[num].timer_dev, PWM_PERIOD_TICKS, pulse);
            #endif

            break;

        case 2:
            latch_state &= ~_BV(MOTOR2_A) & ~_BV(MOTOR2_B);
            MotorController_latch_tx();

            #if ENABLE_PWM
            timer_handles[num].timer_dev =
                timer_open_device(XPAR_IO_SWITCH_0_TIMER1_BASEADDR);
            set_pin(MOTOR2_PWM_PIN, PWM1);
            timer_handles[num].inited = true;
            timer_pwm_generate(
                timer_handles[num].timer_dev, PWM_PERIOD_TICKS, pulse);
            #endif

            break;

        case 3:
            latch_state &= ~_BV(MOTOR3_A) & ~_BV(MOTOR3_B);
            MotorController_latch_tx();

            #if ENABLE_PWM
            timer_handles[num].timer_dev =
                timer_open_device(XPAR_IO_SWITCH_0_TIMER2_BASEADDR);
            set_pin(MOTOR3_PWM_PIN, PWM2);
            timer_handles[num].inited = true;
            timer_pwm_generate(
                timer_handles[num].timer_dev, PWM_PERIOD_TICKS, pulse);
            #endif

            break;

        case 4:
            latch_state &= ~_BV(MOTOR4_A) & ~_BV(MOTOR4_B);
            MotorController_latch_tx();

            #if ENABLE_PWM
            timer_handles[num].timer_dev =
                timer_open_device(XPAR_IO_SWITCH_0_TIMER3_BASEADDR);
            set_pin(MOTOR4_PWM_PIN, PWM3);
            timer_handles[num].inited = true;
            timer_pwm_generate(
                timer_handles[num].timer_dev, PWM_PERIOD_TICKS, pulse);
            #endif

            break;

        default:
            return ERR_INVALID;
    }

    #if DEBUG_MODE
    pyprintf(
        "timer_dev for motor %u: %d\n",
        motornum, timer_handles[num].timer_dev);
    pyprintf(
        "Period: %u, pulse: %u (ticks)\n", PWM_PERIOD_TICKS, pulse);
    #endif

    return SUCCESS;
}

int DCMotor_run
(
    unsigned int motornum,
    unsigned int cmd
)
{
    uint8_t a, b;

    switch (motornum)
    {
        case 1:
            a = MOTOR1_A; b = MOTOR1_B; break;
        case 2:
            a = MOTOR2_A; b = MOTOR2_B; break;
        case 3:
            a = MOTOR3_A; b = MOTOR3_B; break;
        case 4:
            a = MOTOR4_A; b = MOTOR4_B; break;
        default:
            return ERR_INVALID;
    }

    switch (cmd)
    {
        case FORWARD:
            latch_state |= _BV(a);
            latch_state &= ~_BV(b); 
            MotorController_latch_tx();
            break;

        case BACKWARD:
            latch_state &= ~_BV(a);
            latch_state |= _BV(b); 
            MotorController_latch_tx();
            break;

        case RELEASE:
            latch_state &= ~_BV(a);
            latch_state &= ~_BV(b); 
            MotorController_latch_tx();
            break;
        default:
            return ERR_INVALID;
    }

    return SUCCESS;
}

int DCMotor_setSpeed
(
    unsigned int motornum,
    unsigned int speed
)
{
    unsigned int num, pulse;

    #if DEBUG_MODE
    pyprintf(
        "DCMotor_setSpeed called for motor %u, speed: %u\n",
        motornum, speed);
    #endif

    if ((motornum == 0) || (motornum > 4) ||
        (speed    == 0) || (speed    > 100))

    {
        return ERR_INVALID;
    }

    num = motornum - 1;

    if (!timer_handles[num].inited)
    {
        #if DEBUG_MODE
        pyprintf("Timer/PWM not initialized for motor %u\n", motornum);
        #endif

        return ERR_NOTREADY;
    }

    // Calculate the pulse from initial speed input (duty cycle)
    pulse = speed * PWM_PERIOD_TICKS / 100;

    #if ENABLE_PWM
    timer_pwm_stop(timer_handles[num].timer_dev);
    timer_pwm_generate(
        timer_handles[num].timer_dev, PWM_PERIOD_TICKS, pulse);
    #endif

    #if DEBUG_MODE
    pyprintf("DCMotor_setSpeed for motor %u successful\n", motornum);
    pyprintf(
        "Period: %u, pulse: %u (ticks)\n", PWM_PERIOD_TICKS, pulse);
    #endif
    
    return SUCCESS;
}
'''

# Build/load MicroBlaze to IOP PMODA, PMODB and ARDUINO
mb_pmoda = MicroblazeRPC(base.iop_pmoda, source_pmoda)
mb_pmodb = MicroblazeRPC(base.iop_pmodb, source_pmodb)
mb_arduino = MicroblazeRPC(base.iop_arduino, source_arduino)

# SPI helper functions
def get_laser_state(data_byte):
    return ((data_byte >> 7) & 1)

def get_motor_cmd(data_byte):
    return (data_byte & 0xF)

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
    def __init__(self, motornum, init_speed, logger):
        self.motornum = motornum
        self.speed = init_speed
        self.logger = logger

        # Let the first .run() through
        self.direction = -1

        self.logger.debug(f"DCMotor_init called for motor {motornum}")

        err = mb_arduino.DCMotor_init(motornum, init_speed)
        if (err != 0):
            self.logger.error(
                f"DCMotor_init for motor {motornum} failed, err: {err}")
            return
        else:
            self.logger.debug(
                f"DCMotor_init for motor {motornum} successful")

        #self.set_speed_event = threading.Event()
        #self.set_speed_thread = threading.Thread(
        #    target = self.set_speed_t,
        #    args = ())

        #self.set_speed_thread.start()

    #def set_speed_t(self):
    #    print(f"Set speed thread for motor {self.motornum} started")

    def run(self, direction):
        # Short circuit if there's no change, save ourselves a
        # MicroBlaze RPC
        if (direction != self.direction):
            self.logger.debug(
                f"DCMotor_run called for motor {self.motornum}, direction {motor_dir_map[direction]}")

            err = mb_arduino.DCMotor_run(self.motornum, direction)

            if (err != 0):
                self.logger.error(
                    f"DCMotor_run for motor {self.motornum} failed, err: {err}")
                return
            else:
                self.logger.debug(
                    f"DCMotor_run for motor {self.motornum} successful")

    def set_speed(self, speed):
        # Short circuit if there's no change, save ourselves a
        # MicroBlaze RPC
        if (speed != self.speed):
            self.logger.debug(
                f"DCMotor_setSpeed called for motor {self.motornum}, speed {speed}")

            err = mb_arduino.DCMotor_setSpeed(self.motornum, speed)
            if (err != 0):
                self.logger.error(
                    f"DCMotor_setSpeed for motor {self.motornum} failed, err: {err}")
                return
            else:
                self.logger.debug(
                    f"DCMotor_setSpeed for motor {self.motornum} successful")

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

# Main entry point
def run():
    # Game entry point
    car = RC_Car(log_level = logging.INFO)

    car.start()

    # NOTE: Noticed some stale data in SPI sometimes where the
    #       last command comes up at the very beginning. Ignore
    #       this first read and always start from NEUTRAL.
    prev_data = mb_pmoda.spi_read_data()
    prev_dpad_dir = DPAD_NEUTRAL
    car.move(DPAD_NEUTRAL)

    while True:
        data = mb_pmoda.spi_read_data()
        laser = get_laser_state(data)
        dpad_dir = get_motor_cmd(data)

        if dpad_dir >= DPAD_NEUTRAL and dpad_dir <= DPAD_BACKWARD_RIGHT:
            if dpad_dir != prev_dpad_dir:
                car.move(dpad_dir)
                prev_dpad_dir = dpad_dir

        if laser == 1:
            car.fire_laser()

        time.sleep(0.01)

if __name__ == "__main__":
    print(f"Booting application...")
    run()