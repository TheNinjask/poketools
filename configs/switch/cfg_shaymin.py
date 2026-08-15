# Timings
GAME_LOADING_TIME = 1      # Game loading time [s]
BATTLE_LOADING_TIME = 11.7  # Battle loading time [s]


##########################
# MACROS FOR SHINY RESET #
##########################

START_BATTLE = """
A 0.1s
"""

BUSY_WAIT_B = """
LOOP {}
    B 0.1s
    0.1s
"""

RUN_FROM_BATTLE = """
DPAD_UP 0.1s
0.1s
A 0.1s
"""

RELOAD_MAP = """
L_STICK@+000-100 3.1s
0.1s
L_STICK@+000+100 3.2s
"""

RESET_GAME = f"""
{BUSY_WAIT_B.format(6 * 5)}
{RUN_FROM_BATTLE}
{BUSY_WAIT_B.format(5 * 5)}
{RELOAD_MAP}
"""
