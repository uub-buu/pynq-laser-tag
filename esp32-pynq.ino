#include "BluetoothSerial.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"

BluetoothSerial SerialBT;

// ===== Pin mapping (ESP32 Dev Module, VSPI defaults) =====
static constexpr gpio_num_t PIN_SCLK  = GPIO_NUM_18;
static constexpr gpio_num_t PIN_MOSI  = GPIO_NUM_23;
static constexpr gpio_num_t PIN_MISO  = GPIO_NUM_19;
static constexpr gpio_num_t PIN_CS    = GPIO_NUM_5;

static constexpr spi_host_device_t SLAVE_HOST = VSPI_HOST;
static constexpr int TRANSFER_BYTES = 1;

static uint8_t rx_buf[TRANSFER_BYTES];
static uint8_t tx_buf[TRANSFER_BYTES];

void btCallback(esp_spp_cb_event_t event, esp_spp_cb_param_t *param) {
  if (event == ESP_SPP_SRV_OPEN_EVT) {
    Serial.println("✅ Bluetooth client connected!");
  } 
  else if (event == ESP_SPP_CLOSE_EVT) {
    Serial.println("❌ Bluetooth client disconnected!");
  }
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  // pinMode((int)PIN_READY, OUTPUT);
  // digitalWrite((int)PIN_READY, LOW);

  spi_bus_config_t buscfg = {};
  buscfg.mosi_io_num = PIN_MOSI;
  buscfg.miso_io_num = PIN_MISO;
  buscfg.sclk_io_num = PIN_SCLK;
  buscfg.quadwp_io_num = -1;
  buscfg.quadhd_io_num = -1;
  buscfg.max_transfer_sz = TRANSFER_BYTES;

  spi_slave_interface_config_t slvcfg = {};
  slvcfg.spics_io_num = PIN_CS;
  slvcfg.mode = 0;       // SPI mode 0 (match master)
  slvcfg.queue_size = 1;
  slvcfg.flags = 0;

  gpio_set_pull_mode(PIN_CS, GPIO_PULLUP_ONLY);

  // Disable DMA: last arg = 0
  esp_err_t ret = spi_slave_initialize(SLAVE_HOST, &buscfg, &slvcfg, 0);
  if (ret != ESP_OK) {
    Serial.printf("spi_slave_initialize failed: %d\n", (int)ret);
    while (true) delay(1000);
  }

  Serial.println("SPI slave ready. Master must clock EXACTLY 8 bytes per transfer.");

  bool isConnected = SerialBT.begin("esp32-pynq");
  Serial.println(isConnected ? "BT started" : "BT failed");
    // Register callback so we get connect/disconnect events
  SerialBT.register_callback(btCallback);

  Serial.println("Bluetooth SPP started. Waiting for a client...");
  delay(200);
  pinMode(2, OUTPUT);
}
void serialAvailable(int pin){
  digitalWrite(pin, HIGH);
  delay(200);
  digitalWrite(pin, LOW);
  delay(200);
}

void loop() {
  // put your main code here, to run repeatedly:
  static uint32_t counter = 0;

  // // Prepare TX data BEFORE master clocks
  // memset(tx_buf, 0, sizeof(tx_buf));
  // tx_buf[0] = 0xA5;
  // tx_buf[1] = 0x5A;
  // tx_buf[2] = (uint8_t)(counter);
  // tx_buf[3] = (uint8_t)(counter >> 8);
  // tx_buf[4] = (uint8_t)(counter >> 16);
  // tx_buf[5] = (uint8_t)(counter >> 24);

  // memset(rx_buf, 0, sizeof(rx_buf));

  // Optional "ready" signal
 // digitalWrite((int)PIN_READY, HIGH);

  tx_buf[0] = 5;  // <-- send integer value 5 (0x05)

  spi_slave_transaction_t t = {};
  t.length = 8;          // 1 byte = 8 bits
  t.tx_buffer = tx_buf;  // what master reads on MISO
  t.rx_buffer = rx_buf;  // what master sends on MOSI (often dummy)

  // Block until master asserts CS and clocks TRANSFER_BYTES bytes
  esp_err_t ret = spi_slave_transmit(SLAVE_HOST, &t, portMAX_DELAY);

//  digitalWrite((int)PIN_READY, LOW);

  if (ret == ESP_OK) {
    Serial.print("RX: ");
    for (int i = 0; i < TRANSFER_BYTES; i++) {
      Serial.printf("%02X ", rx_buf[i]);
    }
    Serial.println();

    counter++;
  } else {
    Serial.printf("spi_slave_transmit error: %d\n", (int)ret);
    delay(100);
  }
  
  static bool last = false;
  bool now = SerialBT.hasClient();
  if (now != last) {
    Serial.println(now ? "hasClient(): CONNECTED" : "hasClient(): DISCONNECTED");
    last = now;
  }

  if (SerialBT.available() > 0 ) {
    int c = SerialBT.read();
    Serial.println(c);
    Serial.write(c);
    serialAvailable(2);
  }
}
