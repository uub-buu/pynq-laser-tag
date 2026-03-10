#include "BluetoothSerial.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"

BluetoothSerial SerialBT;

// ===== Pin mapping (ESP32 Dev Module, VSPI defaults) =====
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

void btCallback(esp_spp_cb_event_t event, esp_spp_cb_param_t *param) {
  if (event == ESP_SPP_SRV_OPEN_EVT) {
    Serial.println("✅ Bluetooth client connected!");
  } else if (event == ESP_SPP_CLOSE_EVT) {
    Serial.println("❌ Bluetooth client disconnected!");
  }
}

// call me to initalize SPI interface
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

// call me to send cmd via spi
int spi_send_cmd(uint8_t tx_data) {
  tx_buf[0] = tx_data;
  spi_slave_transaction_t t = {};
  t.length = 8;          // 1 byte = 8 bits
  t.tx_buffer = tx_buf;  
  t.rx_buffer = rx_buf; 

  // Block until master asserts CS and clocks TRANSFER_BYTES bytes
  // returns ESP_OK = 0 if valid transmit
  esp_err_t retur_code = spi_slave_transmit(SLAVE_HOST, &t, portMAX_DELAY);

  return retur_code;
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  spi_init();

  // bool isConnected = SerialBT.begin("esp32-pynq");
  // Serial.println(isConnected ? "BT started" : "BT failed");
  // // Register callback so we get connect/disconnect events
  // SerialBT.register_callback(btCallback);

  // Serial.println("Bluetooth SPP started. Waiting for a client...");
  // delay(200);
  // pinMode(2, OUTPUT);
}

void loop() {
  // test serial to SPI to PYNQ
  if (Serial.available() > 0) {
    int console_data = Serial.parseInt();
    esp_err_t ret = spi_send_cmd((uint8_t)console_data);

    if (ret != ESP_OK)  {
      Serial.printf("spi_slave_transmit error: %d\n", (int)ret);
      delay(100);
    }else{
      Serial.print("Sending value to PYNQ: ");
      Serial.println(console_data); 
    }
  }

  // static bool last = false;
  // bool now = SerialBT.hasClient();
  // if (now != last) {
  //   Serial.println(now ? "hasClient(): CONNECTED" : "hasClient(): DISCONNECTED");
  //   last = now;
  // }
}
