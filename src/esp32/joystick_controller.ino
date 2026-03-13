/*******************************************************************************
 * Includes
 ******************************************************************************/

#include "BluetoothSerial.h"


/*******************************************************************************
 * Data
 ******************************************************************************/

BluetoothSerial SerialBT;

/*
 * Pin connections:
 * HW-504 | WROOM
 * GND    - GND
 * +5V    - 3.3V (the readings are off otherwise)
 * VRx    - D2
 * VRy    - D4
 * SW     - RX2
 *
 * Orient the joystick such that the pins are on the left edge.
*/

int     player_num;

uint8_t pin_X   = 2;  /* D2 */
uint8_t pin_Y   = 4;  /* D4 */
uint8_t pin_btn = 16; /* RX2 */

/*
 * NOTE: The potentiometer data from the joystick is encoded into a single byte
 *       direction command (with the MSB indicating button press). Change the
 *       uint8_t if we shift to sending raw potentiometer data. This byte is
 *       what is sent over BT.
 */
volatile uint8_t joystick_data = 0;
volatile bool    joystick_data_available = false;


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

/* Left limits */
#define L_X_MIN  0
#define L_X_MAX  1024
#define L_Y_MIN  1024
#define L_Y_MAX  2048

/* Right limits */
#define R_X_MIN  2048
#define R_X_MAX  4095
#define R_Y_MIN  1024
#define R_Y_MAX  2048

/* Forward limits */
#define F_X_MIN  512
#define F_X_MAX  2048
#define F_Y_MIN  0
#define F_Y_MAX  512

/* Backward limits */
#define B_X_MIN  F_X_MIN
#define B_X_MAX  F_X_MAX
#define B_Y_MIN  2048
#define B_Y_MAX  4095

/* Forward-left limits */
#define FL_X_MIN  0
#define FL_X_MAX  512
#define FL_Y_MIN  FL_X_MIN
#define FL_Y_MAX  FL_X_MAX

/* Forward-right limits */
#define FR_X_MIN  R_X_MIN
#define FR_X_MAX  R_X_MAX
#define FR_Y_MIN  0
#define FR_Y_MAX  512

/* Backward-left limits */
#define BL_X_MIN  FL_X_MIN
#define BL_X_MAX  FL_X_MAX
#define BL_Y_MIN  2048
#define BL_Y_MAX  4095

/* Backward-right limits */
#define BR_X_MIN  FR_X_MIN
#define BR_X_MAX  FR_X_MAX
#define BR_Y_MIN  2048
#define BR_Y_MAX  4095

/* DPAD direction */
#define DPAD_NEUTRAL        0
#define DPAD_LEFT           1
#define DPAD_RIGHT          2
#define DPAD_FORWARD        3
#define DPAD_BACKWARD       4
#define DPAD_FORWARD_LEFT   5
#define DPAD_FORWARD_RIGHT  6
#define DPAD_BACKWARD_LEFT  7
#define DPAD_BACKWARD_RIGHT 8

/*
 * Format of the data (byte) sent over:
 * Bit  7   - Button push state
 * Bits 3:0 - Direction data (0 - 8), see map_to_direction
 */
#define ENCODE_JOYSTICK_DATA(dpad_dir, btn) \
          ((uint8_t)((btn) << 7) | (dpad_dir))


/*******************************************************************************
 * Functions
 ******************************************************************************/

static uint8_t map_to_direction
(
  uint32_t x,
  uint32_t y
)
{
  if (L_X_MIN <= x && x <= L_X_MAX && L_Y_MIN <= y && y <= L_Y_MAX)
    return DPAD_LEFT;
  else if (R_X_MIN <= x && x <= R_X_MAX && R_Y_MIN <= y && y <= R_Y_MAX)
    return DPAD_RIGHT;
  else if (F_X_MIN <= x && x <= F_X_MAX && F_Y_MIN <= y && y <= F_Y_MAX)
    return DPAD_FORWARD;
  else if (B_X_MIN <= x && x <= B_X_MAX && B_Y_MIN <= y && y <= B_Y_MAX)
    return DPAD_BACKWARD;
  else if (FL_X_MIN <= x && x <= FL_X_MAX && FL_Y_MIN <= y && y <= FL_Y_MAX)
    return DPAD_FORWARD_LEFT;
  else if (FR_X_MIN <= x && x <= FR_X_MAX && FR_Y_MIN <= y && y <= FR_Y_MAX)
    return DPAD_FORWARD_RIGHT;
  else if (BL_X_MIN <= x && x <= BL_X_MAX && BL_Y_MIN <= y && y <= BL_Y_MAX)
    return DPAD_BACKWARD_LEFT;
  else if (BR_X_MIN <= x && x <= BR_X_MAX && BR_Y_MIN <= y && y <= BR_Y_MAX)
    return DPAD_BACKWARD_RIGHT;
  else
    return DPAD_NEUTRAL;
}

/* Bluetooth callback to handle various BT serial port protocol events */
void bt_cb
(
  esp_spp_cb_event_t  event,
  esp_spp_cb_param_t *param
)
{
  if (event == ESP_SPP_CLOSE_EVT)
  {
    /* Client disconnected - flush */
    SerialBT.disconnect();
    SerialBT.flush();

    #if DEBUG_MODE
    Serial.println("PYNQ BT client disconnected!");
    #endif
  }
}

/* Initialize BT - called within a task */
void bt_init
(
  void
)
{
  bool bt_inited = false;
  bool bt_begin_done = false;

  while (!bt_inited)
  {
    /* Read the joystick/RC car number on the pin - will be 0 or 1 */
    player_num = digitalRead(PLAYER_NUM_PIN);

    #if DEBUG_MODE
    Serial.print("Initializing BT with name: ");
    Serial.println(BT_JOYSTICK_CLIENT_NAME(player_num));
    #endif

    /*
      * Setup BT with joystick being the slave (second parameter) and disable
      * BLE (third parameter).
      */
    bt_inited =
      SerialBT.begin(BT_JOYSTICK_CLIENT_NAME(player_num), false, true);

    if (!bt_inited)
    {
      #if DEBUG_MODE
      Serial.println("BT failed to initialize, retrying");
      #endif

      SerialBT.end();
      vTaskDelay(pdMS_TO_TICKS(1));
    }
    else
    {
      #if DEBUG_MODE
      Serial.print("Successfully initialized BT with name: ");
      Serial.println(BT_JOYSTICK_CLIENT_NAME(player_num));
      Serial.print("MAC address is: ");
      Serial.println(SerialBT.getBtAddressString());
      #endif

      SerialBT.register_callback(bt_cb);
    }
  }
}

/* Task to send data to PYNQ BT receiver */
void bt_task
(
  void* arg
)
{
  uint8_t  dpad_dir;
  uint32_t V_X, V_Y, btn_pushed;

  /* Initialize BT when starting for the first time */
  bt_init();

  while (1)
  {
    /* Wait till the PYNQ BT receiver connects */
    while (!SerialBT.connected())
    {
      vTaskDelay(pdMS_TO_TICKS(5));

      #if DEBUG_MODE
      Serial.print("Waiting for PYNQ client to connect: ");
      Serial.println(BT_PYNQ_CLIENT_NAME(player_num));
      #endif
    }

    /* Read the joystick input */
    V_X = analogRead(pin_X);
    V_Y = analogRead(pin_Y);
    btn_pushed = 1 - digitalRead(pin_btn);
    dpad_dir = map_to_direction(V_X, V_Y);

    #if DEBUG_MODE
    // X: XXX | Y: YYY | Direction: X | Button: 0/1
    Serial.print("X: ");
    Serial.print(V_X);
    Serial.print(" | ");
    Serial.print("Y: ");
    Serial.print(V_Y);
    Serial.print(" | ");
    Serial.print("Direction: ");
    Serial.print(dpad_dir);
    Serial.print(" | ");
    Serial.print("Button: ");
    Serial.println(btn_pushed);
    #endif

    /* Update the global variable so that the BT task can send data */
    joystick_data = ENCODE_JOYSTICK_DATA(dpad_dir, btn_pushed);

    #ifdef DEBUG_MODE
    Serial.print("Data sent to PYNQ BT receiver over BT: 0x");
    Serial.println(joystick_data, HEX);
    #endif

    SerialBT.write(joystick_data);

    vTaskDelay(pdMS_TO_TICKS(100));
  }
}

void setup
(
  void
)
{
  #if DEBUG_MODE
  Serial.begin(115200);
  while (!Serial);

  for (int i = 0; i < 50; i++)
  {
    Serial.println();
  }
  #endif

  /* Setup joystick pins */
  pinMode(pin_X, INPUT);
  pinMode(pin_Y, INPUT);
  pinMode(pin_btn, INPUT_PULLUP);

  /* Set up the pin to detect joystick/RC car number - 0 or 1 */
  pinMode(PLAYER_NUM_PIN, INPUT);

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
  /* Nothing to do here */
}
