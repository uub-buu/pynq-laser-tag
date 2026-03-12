/*******************************************************************************
 * Includes
 ******************************************************************************/

#include "BluetoothSerial.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"


/*******************************************************************************
 * Macros
 ******************************************************************************/

#define DEBUG_MODE 1

/* NOTE: Some WROOM board pins are special! D2 did not work for this. */
#define PLAYER_NUM_PIN             34 /* D34 */

#define BT_JOYSTICK_CLIENT_P0_ADDR "2C:BC:BB:4B:E5:02"
#define BT_JOYSTICK_CLIENT_P1_ADDR "34:5F:45:A9:B5:2A"

#define BT_PYNQ_CLIENT_P0_NAME     "pynq0"
#define BT_JOYSTICK_CLIENT_P0_NAME "joystick0"

#define BT_PYNQ_CLIENT_P1_NAME     "pynq1"
#define BT_JOYSTICK_CLIENT_P1_NAME "joystick1"


#define BT_JOYSTICK_CLIENT_ADDR(num) \
          num == 0 ? BT_JOYSTICK_CLIENT_P0_ADDR : BT_JOYSTICK_CLIENT_P1_ADDR

#define BT_PYNQ_CLIENT_NAME(num)     \
          num == 0 ? BT_PYNQ_CLIENT_P0_NAME : BT_PYNQ_CLIENT_P1_NAME

#define BT_JOYSTICK_CLIENT_NAME(num) \
          num == 0 ? BT_JOYSTICK_CLIENT_P0_NAME : BT_JOYSTICK_CLIENT_P1_NAME

#define SPI_TIMEOUT_MSEC        10


/*******************************************************************************
 * Data
 ******************************************************************************/

/* BT related global variables */
BluetoothSerial         SerialBT;
bool                    bt_inited = false;

/* SPI related global variables */
static volatile uint8_t spi_tx_data;

/* Pin mapping for ESP-WROOM-32 */
static constexpr gpio_num_t PIN_SCLK = GPIO_NUM_18;
static constexpr gpio_num_t PIN_MISO = GPIO_NUM_19;
static constexpr gpio_num_t PIN_MOSI = GPIO_NUM_23;
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
 * Functions
 ******************************************************************************/

/* Initialize BT - called within a task */
void bt_init
(
  void
)
{
  int          player_num;
  bool         bt_inited = false;
  bool         bt_begin_done = false;
  unsigned int bt_connection_attempt = 1;

  while (!bt_inited)
  {
    /* Read the player/RC car number on the pin - will be 0 or 1 */
    player_num = digitalRead(PLAYER_NUM_PIN);

    bt_begin_done = false;

    #if DEBUG_MODE
    Serial.print("Initializing BT with name: ");
    Serial.println(BT_PYNQ_CLIENT_NAME(player_num));
    #endif

    while (!bt_begin_done)
    {
      /*
       * Setup BT with PYNQ being the master (second parameter) and disable BLE
       * (third parameter).
       */
      bt_begin_done =
        SerialBT.begin(BT_PYNQ_CLIENT_NAME(player_num), true, true);

      if (!bt_begin_done)
      {
        #if DEBUG_MODE
        Serial.println("BT failed to initialize, retrying");
        #endif

        vTaskDelay(pdMS_TO_TICKS(1));
      }
    }

    #if DEBUG_MODE
    Serial.print("Successfully initialized BT with name: ");
    Serial.println(BT_PYNQ_CLIENT_NAME(player_num));
    #endif

    /* Connect to the joystick controller BT */
    if (SerialBT.connect(BTAddress(BT_JOYSTICK_CLIENT_ADDR(player_num))))
    {
      #if DEBUG_MODE
      Serial.print("Connected to joystick controller on attempt ");
      Serial.println(bt_connection_attempt);
      #endif

      bt_inited = true;
    }
    else
    {
      bt_connection_attempt++;

      #if DEBUG_MODE
      Serial.println("Could not connect to joystick controller, retrying");
      #endif

      SerialBT.end();

      /*
      * Wait 1 second for the joystick controller to detect disconnection and
      * clean up.
      */
      vTaskDelay(pdMS_TO_TICKS(1000));
    }
  }
}

/* Initialize the ESP32 board as SPI slave device */
esp_err_t spi_init
(
  void
)
{
  gpio_set_pull_mode(PIN_CS, GPIO_PULLUP_ONLY);

  return spi_slave_initialize(SLAVE_HOST, &buscfg, &slvcfg, 0);
}

/* Task to send data to the SPI master (PYNQ-Z2) */
void spi_task
(
  void* arg
)
{
  while (1)
  {
    tx_buf[0] = spi_tx_data;

    spi_slave_transaction_t t =
    {
      .length    = 8 * TRANSFER_BYTES,
      .tx_buffer = tx_buf,
      .rx_buffer = rx_buf,
    };

    /*
     * (Timed) wait for the master to assert CS and complete the transfer.
     * Don't care if it times out either - just send the next byte.
     * Indefinite block does not work for us since a single transfer failure for
     * any reason is not catastrophic.
     */
    spi_slave_transmit(SLAVE_HOST, &t, pdMS_TO_TICKS(SPI_TIMEOUT_MSEC));

    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

/* Task to connect to joystick controller BT */
void bt_task
(
  void* arg
)
{
  /*
   * NOTE: The data from the joystick is a single byte. Change the uint8_t if we
   *       shift to sending raw potentiometer data.
   */
  uint8_t bt_data;

  /* Initialize BT when starting for the first time */
  bt_init();

  while (1)
  {
    if (SerialBT.available() > 0)
    {
      /* Read the command over BT */
      bt_data = SerialBT.read();
      #if DEBUG_MODE
      Serial.print("Data from joystick: ");
      Serial.println(bt_data);
      #endif

      /*
      * Sanity check if data received from the joystick is in the expected
      * range.
      */
      if (bt_data > 255)
      {
        return;
      }

      /* Update the global variable so that the SPI task can send data */
      spi_tx_data = bt_data;
    }

    vTaskDelay(pdMS_TO_TICKS(1));
  }
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

  /* Set up the pin to detect player/RC car number - 0 or 1 */
  pinMode(PLAYER_NUM_PIN, INPUT);

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

  /*
   * Start a task to try to send data over SPI. When we try do this in loop(),
   * we kept seeing timer group 1 WDT (TG1WDT) failures when PYNQ does a
   * spi_transfer().
   */
  xTaskCreate(spi_task, "spi_task", 4096, NULL, 1, NULL);

  /*
   * Start a BT task to connect to the joystick controller. When we try to do
   * this in loop(), any failure leads to instability in BT connection - causing
   * multiple reboots.
   */
  xTaskCreate(bt_task, "bt_task", 4096, NULL, 1, NULL);
}

void loop
(
  void
)
{
  /*
   * Nothing to do - loop() is practically a sandbox. We ran into *multiple*
   * issues with handling BT connection & SPI Tx within this. Ultimately, we
   * moved to tasks.
   */
}
