/*******************************************************************************
 * Includes
 ******************************************************************************/

#include "BluetoothSerial.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"
//#include "esp_heap_caps.h"


/*******************************************************************************
 * Data
 ******************************************************************************/

BluetoothSerial SerialBT;

/* Pin mapping for ESP-WROOM-32 */
static constexpr gpio_num_t PIN_SCLK = GPIO_NUM_18;
static constexpr gpio_num_t PIN_MOSI = GPIO_NUM_23;
static constexpr gpio_num_t PIN_MISO = GPIO_NUM_19;
static constexpr gpio_num_t PIN_CS = GPIO_NUM_5;

static constexpr spi_host_device_t SLAVE_HOST = VSPI_HOST;
static constexpr int TRANSFER_BYTES = 1;

static uint8_t rx_buf[TRANSFER_BYTES];
static uint8_t tx_buf[TRANSFER_BYTES];

spi_bus_config_t buscfg =
{
  .mosi_io_num     = PIN_MOSI,
  .miso_io_num     = PIN_MISO,
  .sclk_io_num     = PIN_SCLK,
  .quadwp_io_num   = -1,
  .quadhd_io_num   = -1,
  .max_transfer_sz = TRANSFER_BYTES,
};

spi_slave_interface_config_t slvcfg =
{
  .spics_io_num = PIN_CS,
  .flags        = 0,
  .queue_size   = 1,
  .mode         = 0,  /* SPI mode 0 (match master) */
};


/*******************************************************************************
 * Macros
 ******************************************************************************/

#define DEBUG_MODE 1

#define BT_JOYSTICK_CLIENT_NAME "joystick0"
#define BT_JOYSTICK_CLIENT_ADDR "2C:BC:BB:4B:E5:02"
#define BT_PYNQ_CLIENT_NAME     "pynq0"


/*******************************************************************************
 * Functions
 ******************************************************************************/

/* Initialize the ESP32 board as SPI slave device */
esp_err_t spi_init
(
  void
)
{
  gpio_set_pull_mode(PIN_CS, GPIO_PULLUP_ONLY);

  return spi_slave_initialize(SLAVE_HOST, &buscfg, &slvcfg, 0);
}

/* Transmit command to the SPI master (PYNQ-Z2) */
esp_err_t spi_send_data
(
  uint8_t tx_data
)
{
  tx_buf[0] = tx_data;
  spi_slave_transaction_t t = {};
  t.length = 8;  // 1 byte = 8 bits
  t.tx_buffer = tx_buf;
  t.rx_buffer = rx_buf;

  /*
   * Wait for 1 millisecond for the master to assert CS and complete the
   * transfer.
   * Indefinite block does not work for us since a single transfer failure for
   * any reason is not catastrophic.
   */
  return spi_slave_transmit(SLAVE_HOST, &t, pdMS_TO_TICKS(1));
}

void setup
(
  void
)
{
  esp_err_t ret = ESP_FAIL;

#if DEBUG_MODE
  Serial.begin(115200);

  /* Clear out the serial console for a fresh start */
  for (int i = 0; i < 50; i++)
  {
    Serial.println();
  }
#endif

#if DEBUG_MODE
  Serial.println("Initializing SPI slave");
#endif

  /* Initialize SPI on ESP32 Module*/
  ret = spi_init();

  if (ret != ESP_OK)
  {
#if DEBUG_MODE
    Serial.print("spi_init failed, err: ");
    Serial.println(ret);
#endif
    exit(1);
  }

#if DEBUG_MODE
  Serial.print("Initializing BT with name: ");
  Serial.println(BT_PYNQ_CLIENT_NAME);
#endif

  /*
   * Setup BT with PYNQ being the master (second parameter) and disable BLE
   * (third parameter).
   */
  if (!SerialBT.begin(BT_PYNQ_CLIENT_NAME, true))
  {
    /* Fatal error/exit if BT setup failed */
#if DEBUG_MODE
    Serial.println("BT failed to initialize");
#endif
    exit(1);
  }

#if DEBUG_MODE
  Serial.print("Successfully initialized BT with name: ");
  Serial.println(BT_PYNQ_CLIENT_NAME);
#endif

  /* Connect to the joystick controller BT */
  if (SerialBT.connect(BTAddress(BT_JOYSTICK_CLIENT_ADDR)))
  {
#if DEBUG_MODE
    Serial.println("Connected to joystick controller!");
#endif
  }
  else
  {
#if DEBUG_MODE
    Serial.println("Could not connect to joystick controller!");
#endif
    exit(1);
  }
}

void loop
(
  void
)
{
  uint8_t   cmd; /* The command from the joystick is a single byte */
  esp_err_t ret = ESP_FAIL;

  if (SerialBT.available() > 0)
  {
    /* Read the command over BT */
    cmd = SerialBT.read();
#if DEBUG_MODE
    Serial.print("Direction command: ");
    Serial.println(cmd);
#endif

    /*
     * Sanity check if command byte received from the joystick is in the
     * expected range.
     */
    if (cmd > 8)
    {
      /* This restarts the loop() - single byte failure is not catastrophic */
      return;
    }

    /* Send the command (single byte) over SPI to PYNQ board */
    ret = spi_send_data(cmd);
    if (ret != ESP_OK)
    {
      /*
       * In case of a failure, log it - but keep trying to send more since a
       * single byte transfer failure is not catastrophic.
       */
#if DEBUG_MODE
      Serial.print("spi_send_data failed, err: ");
      Serial.println(ret);
#endif
    }
  }

  delay(50);
}
