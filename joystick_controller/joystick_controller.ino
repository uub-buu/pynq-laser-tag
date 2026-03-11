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

uint8_t pin_X   = 2;  /* D2 */
uint8_t pin_Y   = 4;  /* D4 */
uint8_t pin_btn = 16; /* RX2 */


/*******************************************************************************
 * Macros
 ******************************************************************************/

#define DEBUG_MODE 1

#define BT_JOYSTICK_CLIENT_NAME "joystick1"
#define BT_PYNQ_CLIENT_NAME     "pynq1"

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


/*******************************************************************************
 * Functions
 ******************************************************************************/

/*
 * Left           - 1
 * Right          - 2
 * Forward        - 3
 * Backward       - 4
 * Forward left   - 5
 * Forward right  - 6
 * Backward left  - 7
 * Backward right - 8
 * Neutral        - 0
 */
static uint8_t map_to_direction
(
  uint32_t x,
  uint32_t y
)
{
  if (L_X_MIN <= x && x <= L_X_MAX && L_Y_MIN <= y && y <= L_Y_MAX)
    return 1;
  else if (R_X_MIN <= x && x <= R_X_MAX && R_Y_MIN <= y && y <= R_Y_MAX)
    return 2;
  else if (F_X_MIN <= x && x <= F_X_MAX && F_Y_MIN <= y && y <= F_Y_MAX)
    return 3;
  else if (B_X_MIN <= x && x <= B_X_MAX && B_Y_MIN <= y && y <= B_Y_MAX)
    return 4;
  else if (FL_X_MIN <= x && x <= FL_X_MAX && FL_Y_MIN <= y && y <= FL_Y_MAX)
    return 5;
  else if (FR_X_MIN <= x && x <= FR_X_MAX && FR_Y_MIN <= y && y <= FR_Y_MAX)
    return 6;
  else if (BL_X_MIN <= x && x <= BL_X_MAX && BL_Y_MIN <= y && y <= BL_Y_MAX)
    return 7;
  else if (BR_X_MIN <= x && x <= BR_X_MAX && BR_Y_MIN <= y && y <= BR_Y_MAX)
    return 8;
  else
    return 0;
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

  Serial.print("Initializing BT with name: ");
  Serial.println(BT_JOYSTICK_CLIENT_NAME);
  #endif

  /* Setup joystick pins */
  pinMode(pin_X, INPUT);
  pinMode(pin_Y, INPUT);
  pinMode(pin_btn, INPUT_PULLUP);

  /*
   * Setup BT with joystick being the slave (second parameter) and disable BLE
   * (third parameter).
   */
  if (!SerialBT.begin(BT_JOYSTICK_CLIENT_NAME))
  {
    /* Fatal error/exit if BT setup failed */
    #if DEBUG_MODE
    Serial.println("BT failed to initialize");
    #endif
    exit(1);
  }

  #if DEBUG_MODE
  Serial.print("Successfully initialized BT with name: ");
  Serial.println(BT_JOYSTICK_CLIENT_NAME);
  Serial.println(SerialBT.getBtAddressString());
  delay(1000);
  #endif
}

void loop
(
  void
)
{
  uint8_t  cmd;
  uint32_t V_X, V_Y, btn_pushed;

  /* Wait till the PYNQ BT receiver connects */
  while (!SerialBT.connected())
  {
    delay(5);
    Serial.println("Waiting for PYNQ client to connect");
  }

  /* Read the joystick input */
  V_X = analogRead(pin_X);
  V_Y = analogRead(pin_Y);
  btn_pushed = 1 - digitalRead(pin_btn);
  cmd = map_to_direction(V_X, V_Y);

  #if DEBUG_MODE
  // X: XXX | Y: YYY | Direction: X | Button: 0/1
  Serial.print("X: ");
  Serial.print(V_X);
  Serial.print(" | ");
  Serial.print("Y: ");
  Serial.print(V_Y);
  Serial.print(" | ");
  Serial.print("Direction: ");
  Serial.print(cmd);
  Serial.print(" | ");
  Serial.print("Button: ");
  Serial.println(btn_pushed);
  #endif

  /* Send it over via BT */
  /*
   * Format of the data (byte) sent over:
   * Bit  7   - Button push state
   * Bits 3:0 - Direction data (0 - 8), see map_to_direction
   */
  cmd = ((uint8_t)(btn_pushed << 7) | cmd);
  #ifdef DEBUG_MODE
  Serial.print("Command byte sent over: 0x");
  Serial.println(cmd, HEX);
  #endif
  SerialBT.write(cmd);

  delay(100);
}
