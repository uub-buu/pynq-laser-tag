#include "BluetoothSerial.h"

BluetoothSerial SerialBT;

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
  delay(500);
  digitalWrite(pin, LOW);
  delay(500);
}

void loop() {
  // put your main code here, to run repeatedly:

  static bool last = false;
  bool now = SerialBT.hasClient();
  if (now != last) {
    Serial.println(now ? "hasClient(): CONNECTED" : "hasClient(): DISCONNECTED");
    last = now;
  }

  if (SerialBT.available()) {
    int c = SerialBT.read();
    Serial.write(c);
    serialAvailable(2);
  }
}
