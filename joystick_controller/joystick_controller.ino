#define DEBUG_MODE 1

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

uint32_t V_X, V_Y, btn_pushed;

void setup() {
  #if DEBUG_MODE
  Serial.begin(9600);
  #endif

  pinMode(pin_X, INPUT);
  pinMode(pin_Y, INPUT);
  pinMode(pin_btn, INPUT_PULLUP);

  V_X = V_Y = btn_pushed = 0;
}

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

static char* map_to_direction(uint32_t x, uint32_t y) {
  if (L_X_MIN <= x && x <= L_X_MAX && L_Y_MIN <= y && y <= L_Y_MAX)
    return "L";
  else if (R_X_MIN <= x && x <= R_X_MAX && R_Y_MIN <= y && y <= R_Y_MAX)
    return "R";
  else if (F_X_MIN <= x && x <= F_X_MAX && F_Y_MIN <= y && y <= F_Y_MAX)
    return "F";
  else if (B_X_MIN <= x && x <= B_X_MAX && B_Y_MIN <= y && y <= B_Y_MAX)
    return "B";
  else if (FL_X_MIN <= x && x <= FL_X_MAX && FL_Y_MIN <= y && y <= FL_Y_MAX)
    return "FL";
  else if (FR_X_MIN <= x && x <= FR_X_MAX && FR_Y_MIN <= y && y <= FR_Y_MAX)
    return "FR";
  else if (BL_X_MIN <= x && x <= BL_X_MAX && BL_Y_MIN <= y && y <= BL_Y_MAX)
    return "BL";
  else if (BR_X_MIN <= x && x <= BR_X_MAX && BR_Y_MIN <= y && y <= BR_Y_MAX)
    return "BR";
  else
    return "N";
}

void loop() {
  V_X = analogRead(pin_X);
  V_Y = analogRead(pin_Y);
  btn_pushed = 1 - digitalRead(pin_btn);

  #ifdef DEBUG_MODE
  // X: XXX | Y: YYY | Direction: X | Button: 0/1
  Serial.print("X: ");
  Serial.print(V_X);
  Serial.print(" | ");
  Serial.print("Y: ");
  Serial.print(V_Y);
  Serial.print(" | ");
  Serial.print("Direction: ");
  Serial.print(map_to_direction(V_X, V_Y));
  Serial.print(" | ");
  Serial.print("Button: ");
  Serial.println(btn_pushed);
  #endif

  delay(100);
}
