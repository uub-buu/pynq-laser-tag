/*******************************************************************************
 * Includes
 ******************************************************************************/

#include "BluetoothSerial.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"

/*******************************************************************************
 * Data
 ******************************************************************************/

BluetoothSerial SerialBT;

// Pin mapping for ESP-WROOM-32
static constexpr gpio_num_t PIN_SCLK = GPIO_NUM_18;
static constexpr gpio_num_t PIN_MOSI = GPIO_NUM_23;
static constexpr gpio_num_t PIN_MISO = GPIO_NUM_19;
static constexpr gpio_num_t PIN_CS = GPIO_NUM_5;

static constexpr spi_host_device_t SLAVE_HOST = VSPI_HOST;
static constexpr int TRANSFER_BYTES = 1;

static uint8_t rx_buf[TRANSFER_BYTES];
static uint8_t tx_buf[TRANSFER_BYTES];

//bus configuration profile
spi_bus_config_t buscfg = {};
//spi slave configuration profile
spi_slave_interface_config_t slvcfg = {};

/*******************************************************************************
 * Macros
 ******************************************************************************/

#define DEBUG_MODE 1

#define BT_JOYSTICK_CLIENT_NAME "joystick0"
#define BT_JOYSTICK_CLIENT_ADDR "2C:BC:BB:4B:E5:02"
#define BT_PYNQ_CLIENT_NAME "pynq0"


/*******************************************************************************
 * Functions
 ******************************************************************************/
/*
 * Initialize the SPI interface on the ESP32 Module
 */
void spi_init() {
  //configure SPI bus
  buscfg.mosi_io_num = PIN_MOSI;
  buscfg.miso_io_num = PIN_MISO;
  buscfg.sclk_io_num = PIN_SCLK;
  buscfg.quadwp_io_num = -1;
  buscfg.quadhd_io_num = -1;
  buscfg.max_transfer_sz = TRANSFER_BYTES;

  //configure SPI slave
  slvcfg.spics_io_num = PIN_CS;
  slvcfg.mode = 0;  // SPI mode 0 (match master)
  slvcfg.queue_size = 1;
  slvcfg.flags = 0;
  gpio_set_pull_mode(PIN_CS, GPIO_PULLUP_ONLY);

  //initialize SPI slave
  esp_err_t ret = spi_slave_initialize(SLAVE_HOST, &buscfg, &slvcfg, 0);
  if (ret != ESP_OK) {
    Serial.printf("spi_slave_initialize failed: %d\n", (int)ret);
    while (true) delay(1000);
  } else {
    Serial.println("SPI slave ready. Master must clock EXACTLY 8 bytes per transfer.");
  }
}

/*
 * Transmit command to the SPI Master(PYNQ-Z2)
 */
int spi_send_cmd(uint8_t tx_data) {
  tx_buf[0] = tx_data;
  spi_slave_transaction_t t = {};
  t.length = 8;  // 1 byte = 8 bits
  t.tx_buffer = tx_buf;
  t.rx_buffer = rx_buf;

  // Block until master asserts CS and clocks TRANSFER_BYTES bytes
  // returns ESP_OK = 0 if valid transmit
  esp_err_t retur_code = spi_slave_transmit(SLAVE_HOST, &t, portMAX_DELAY);

  return retur_code;
}

void setup(
  void) {
#if DEBUG_MODE
  Serial.begin(115200);

  for (int i = 0; i < 50; i++) {
    Serial.println();
  }
  Serial.print("Initializing BT with name: ");
  Serial.println(BT_PYNQ_CLIENT_NAME);
#endif
  /* Initialize SPI on ESP32 Module*/
   spi_init();
  /*
   * Setup BT with PYNQ being the master (second parameter) and disable BLE
   * (third parameter).
   */
  if (!SerialBT.begin(BT_PYNQ_CLIENT_NAME, true)) {
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
  if (SerialBT.connect(BTAddress(BT_JOYSTICK_CLIENT_ADDR))) {
#if DEBUG_MODE
    Serial.println("Connected to joystick controller!");
#endif
  } else {
#if DEBUG_MODE
    Serial.println("Could not connect to joystick controller!");
#endif
    exit(1);
  }
}

void loop(
  void) {
  uint8_t cmd;

  if (SerialBT.available() > 0) {
    /* Read the command over BT */
    cmd = SerialBT.read();
    esp_err_t ret = spi_send_cmd(cmd);
#if DEBUG_MODE
    Serial.print("Direction command: ");
    Serial.println(cmd);
#endif
  }

  /* TODO: Send it over SPI to PYNQ board */
  /*
   * NOTE: For now, let's just send this uint8_t over to PYNQ via SPI and decode
   *       the byte in PYNQ in accordance with mapping (check map_to_direction
   *       in joystick_controller.ino).
   */

  delay(50);
}
