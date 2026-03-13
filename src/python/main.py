import subprocess, multiprocessing, logging

from pynq.overlays.base import BaseOverlay
from pynq.lib.pynqmicroblaze.rpc import MicroblazeRPC

from pmoda import source_pmoda
from pmodb import source_pmodb
from pmod_arduino import source_arduino
from rc_car import RC_Car

def game_p(mb_pmoda, mb_pmodb, mb_arduino):
    car = RC_Car(mb_pmoda, mb_pmodb, mb_arduino, log_level = logging.DEBUG)

    car.start()
    car.wait_for_stop()

    return

# Main entry point
def run():
    base = BaseOverlay("base.bit")
    mb_pmoda = MicroblazeRPC(base.iop_pmoda, source_pmoda)
    mb_pmodb = MicroblazeRPC(base.iop_pmodb, source_pmodb)
    mb_arduino = MicroblazeRPC(base.iop_arduino, source_arduino)

    # Spawn a game process and bind it to CPU1
    game_proc = multiprocessing.Process(
        target=game_p, args=(mb_pmoda, mb_pmodb, mb_arduino))

    game_proc.start()

    subprocess.run(
        f"taskset -p 0x2 {game_proc.pid}",
        shell = True,
        stdout = subprocess.DEVNULL,
        stderr = subprocess.DEVNULL)

    # Wait for the game process to finish
    game_proc.join()

if __name__ == "__main__":
    run()
