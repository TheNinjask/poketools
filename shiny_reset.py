"""
Automates resets for shiny hunting stationary Pokémon.
"""

import os
import importlib.util
from utils import audio
from utils.controller import Controller
import argparse
from configs import general


# Configuration variables
DEFAULT_REC_DURATION = 4  # Default game sound recording duration [s], overridable per scenario via REC_DURATION in its cfg_*.py file

# Template audio file
script_directory = os.path.dirname(os.path.abspath(__file__))  # current directory
SHINY_AUDIO_FILE = f"{script_directory}/template_sounds/shiny/template_cropped.wav"  # expected shiny sound to find

# Number of resets
number_of_resets = 0


if __name__ == "__main__":

    # Console model (determines which scenarios/timings are available)
    possible_models = sorted([
        directory for directory in os.listdir(f"{script_directory}/configs")
        if os.path.isdir(f"{script_directory}/configs/{directory}") and directory != "__pycache__"
    ])
    # Pre-parse just the model flag, since it determines the valid --scenario choices below
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-m", "--model", choices=possible_models, default="switch")
    pre_args, _ = pre_parser.parse_known_args()
    scenarios_directory = f"{script_directory}/configs/{pre_args.model}"
    possible_scenarios = [filename.split(".")[0][4:] for filename in os.listdir(scenarios_directory) if filename[0:4] == "cfg_"]

    # Command line arguments
    parser = argparse.ArgumentParser()
    help = "Use this flag to specify what console model the macros and timings should be tuned for. " \
           "This determines which scenarios are available (see --scenario)."
    parser.add_argument("-m", "--model", help=help, choices=possible_models, default="switch")
    # Scenario (Pokemon we are trying to catch)
    help = f"Use this flag to specify what scenario the macros and timings should be set for " \
           f"(available scenarios depend on --model; for '{pre_args.model}': {', '.join(possible_scenarios)}). " \
           "If the scenario you need is implemented, please contribute by adding it to the `configs` directory."
    default_scenario = "ramanas" if "ramanas" in possible_scenarios else possible_scenarios[0]
    parser.add_argument("-s", "--scenario", help=help, choices=possible_scenarios, default=default_scenario)
    # Capture screenshot or video when shiny is found
    help = "Capture a video or screenshot once a shiny is found."
    parser.add_argument("-c", "--capture", help=help, choices=["video", "screenshot"])
    # Support for consoles with multiple users
    help = "Indicate the number of the user (1-8) that should be used to start the game, " \
           "or 0 if there is only one user that is selected automatically."
    list_users = [str(u) for u in range(0, 9)]
    parser.add_argument("-u", "--user", help=help, choices=list_users, default="0")
    # Plot correlation
    help = "Use this flag to save a plot of the correlation between the recorded audio " \
           "and the shiny sparkles audio template."
    parser.add_argument("-p", "--plot-correlation", help=help, action="store_true")
    help = "Select an audio input device by its name. Audio devices can be listed with `python3 -m sounddevice`."
    parser.add_argument("-d", "--device", help=help)
    help = "Run a fixed number of battle/recording iterations (default 1), even if no shiny is found, and save " \
           "the audio recording used for each matching attempt. Useful for checking timings and listening to " \
           "what the code hears."
    parser.add_argument("-n", "--dry-run", help=help, type=int, nargs="?", const=1, default=None, metavar="CYCLES")
    args = parser.parse_args()

    # Load the scenario config from the selected console model's directory
    config_path = f"{script_directory}/configs/{args.model}/cfg_{args.scenario}.py"
    config_spec = importlib.util.spec_from_file_location(f"cfg_{args.scenario}", config_path)
    config = importlib.util.module_from_spec(config_spec)
    config_spec.loader.exec_module(config)

    # Recording duration: use the scenario's own REC_DURATION if it defines one, otherwise the default
    recording_duration = getattr(config, "REC_DURATION", DEFAULT_REC_DURATION)

    # Force no user switch for Shaymin scenario
    if args.scenario == "shaymin":
        args.user = "0"

    # Confirm audio device exists
    if args.device:
        audio.assign_device(args.device)

    # Initialize and connect virtual game controller, then go back to game
    controller = Controller()
    controller.sync_and_go_back()

    is_shiny = False
    cycle = 0
    while not is_shiny:
        cycle += 1
        # Initiate battle with Pokemon
        print(f"Initiating a battle.")
        controller.macro(config.START_BATTLE)
        # Wait for the shiny sparkles to appear,
        # while using the controller to prevent it from disconnecting
        controller.busy_wait(config.BATTLE_LOADING_TIME)
        # Record game sound, and check if shiny sparkles are present
        controller.busy_wait_background(recording_duration)
        dry_run_recording_path = f"{script_directory}/dry_run_recording_{cycle}.wav" if args.dry_run else None
        is_shiny, correlation = audio.record_and_check_shiny(SHINY_AUDIO_FILE, recording_duration, dry_run_recording_path)
        if is_shiny:
            print(f"Shiny found after {number_of_resets} resets.")
            # Shiny ! Put console in sleep mode
            if args.capture == "video":
                controller.macro(general.VIDEO)
                controller.busy_wait_b(8)
            elif args.capture == "screenshot":
                controller.macro(general.SCREENSHOT)
            controller.macro(general.SLEEP_MODE)
            if args.plot_correlation:
                audio.save_plot(correlation, f"{script_directory}/correlation.png")
            exit(0)
        elif args.dry_run and cycle >= args.dry_run:
            print(f"Dry run complete after {cycle} cycle(s). No shiny found.")
            controller.macro(general.SLEEP_MODE)
            exit(0)
        else:
            # Not shiny, reset game
            number_of_resets += 1
            if args.dry_run:
                print(f"Dry run cycle {cycle}/{args.dry_run} complete. No shiny found. Resetting for next cycle.")
            else:
                print(f"No shiny found. Reset n°{number_of_resets}.")
            controller.reset(config.RESET_GAME, int(args.user))
            controller.busy_wait(config.GAME_LOADING_TIME)
