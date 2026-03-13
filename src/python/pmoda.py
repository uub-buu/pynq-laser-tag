from pynq.overlays.base import BaseOverlay
from pynq.lib.pynqmicroblaze.rpc import MicroblazeRPC

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

