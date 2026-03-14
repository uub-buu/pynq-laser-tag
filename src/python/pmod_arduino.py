# Derived from https://github.com/adafruit/Adafruit-Motor-Shield-library

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
    // NOTE: Stopping and then restarting PWM with a new frequency
    //       caused the motors to stop intermittently. Maybe because
    //       PWM stop would signal the motor driver to "stop"?
    // timer_pwm_stop(timer_handles[num].timer_dev);
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
