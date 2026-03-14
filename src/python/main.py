import time, subprocess, multiprocessing, logging

from pynq.overlays.base import BaseOverlay
from pynq.lib.pynqmicroblaze.rpc import MicroblazeRPC

from pmoda import source_pmoda
from pmodb import source_pmodb
from pmod_arduino import source_arduino
from rc_car import RC_Car

# Constants

GAME_MODE_SUDDEN_DEATH  = 0
GAME_MODE_THREE_STRIKES = 1

primary_game_mode = GAME_MODE_SUDDEN_DEATH
secondary_game_mode = GAME_MODE_THREE_STRIKES

def game_p(mb_pmoda, mb_pmodb, mb_arduino, game_mode):
    car = RC_Car(
        mb_pmoda, mb_pmodb, mb_arduino,
        game_mode,
        weapons = True,
        status_led = True,
        log_level = logging.ERROR)

    car.start()
    car.wait_for_stop()

# Main entry point
def run():
    base = BaseOverlay("base.bit")

    mb_pmoda = MicroblazeRPC(base.iop_pmoda, source_pmoda)
    mb_pmodb = MicroblazeRPC(base.iop_pmodb, source_pmodb)
    mb_arduino = MicroblazeRPC(base.iop_arduino, source_arduino)

    game_mode = primary_game_mode

    while True:
        # Spawn the game process and bind it to CPU1
        game_proc = multiprocessing.Process(
            target=game_p, args=(mb_pmoda, mb_pmodb, mb_arduino, game_mode))

        game_proc.start()

        # Wait for the game process to finish
        game_proc.join()

        subprocess.run(
            f"taskset -p 0x2 {game_proc.pid}",
            shell = True,
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL)

        # After the first game stops, let a user press any on-board
        # PYNQ push buttons to restart the game
        while True:
            btns = base.btns_gpio.read()
            if btns == 0:
                time.sleep(0.1)

            # If button 3 was pressed, change the game mode to secondary
            elif btns == (1 << 3):
                game_mode = secondary_game_mode
                break

            # If any other button was pressed, use the primary game mode
            else:
                game_mode = primary_game_mode
                break

if __name__ == "__main__":
    # Never returns
    run()
