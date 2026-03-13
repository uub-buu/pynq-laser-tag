
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
