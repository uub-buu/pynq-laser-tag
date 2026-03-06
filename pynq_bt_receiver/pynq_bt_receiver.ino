/*******************************************************************************
 * Includes
 ******************************************************************************/

#include "BluetoothSerial.h"


/*******************************************************************************
 * Data
 ******************************************************************************/

BluetoothSerial SerialBT;


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

void setup
(
  void
)
{
  #if DEBUG_MODE
  Serial.begin(115200);

  for (int i = 0; i < 50; i++)
  {
    Serial.println();
  }
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
  uint8_t cmd;

  if (SerialBT.available() > 0)
  {
    /* Read the command over BT */
    cmd = SerialBT.read();
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
