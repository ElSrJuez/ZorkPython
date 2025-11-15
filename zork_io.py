from zork_logging import game_log, system_log, game_log_json
import inspect
from zork_ui import RichZorkUI
from completions import stream_to_ui, MAX_LOG_LINES

# Rolling history of game outputs and commands
INTERACTIONS: list[str] = []

_ui: RichZorkUI | None = None

def _ui_instance():
    global _ui
    if _ui is None:
        _ui = RichZorkUI()
        _ui.start()
    return _ui

# redefine input( as zork_input( which is a wrapper that can be used to process input text before passing it to zork

# this is an object that collects all printed strings as a collection, adding an attribute with the name of the function that called zork_print(
_PRINT_CACHE = []

def zork_input(prompt=''):
    # Log the command as a game action
    message_collection = collect_printed_messages()
    # collect only the message text
    messages_only = [msg for msg, caller in message_collection]
    ui = _ui_instance()

    # Send recent interaction history to AI helper before prompting
    stream_to_ui(ui, INTERACTIONS[-MAX_LOG_LINES:])

    # Now read user input
    user_input = ui.read_prompt(prompt)
    game_log(user_input)
    # Echo the command in light green within the Zork output pane
    ui.append_zork(f"[bright_green]> {user_input}[/]")
    # Store user command in uppercase for AI context
    INTERACTIONS.append(f"> {user_input.upper()}")
    return user_input

def zork_print(message=""):
    ui = _ui_instance()
    ui.append_zork(message)

    # Record into INTERACTIONS if not a duplicate of the last entry
    if message and (not INTERACTIONS or INTERACTIONS[-1] != message):
        INTERACTIONS.append(message)
    
    try:
        # Use .function for modern Python (3.5+) as the frame records are named tuples
        caller_name = inspect.stack()[1].function
    except IndexError:
        caller_name = "Unknown (called from module level or outside a function)"
    except AttributeError:
        # Fallback for older versions or other cases
        caller_name = inspect.stack()[1][3]

    _PRINT_CACHE.append((message, caller_name))
    system_log(f"Printed message: {message} (from {caller_name})")
    
def collect_printed_messages():
    """
    Returns the collected printed messages and clears the cache.
    Each entry is a tuple of (caller_name, message).
    Also appends these messages to the global INTERACTIONS for AI context.
    """
    global _PRINT_CACHE, INTERACTIONS
    collected = _PRINT_CACHE[:]
    game_log_json({"printed_messages": collected})
    _PRINT_CACHE = []
    # Extract just message texts and record
    messages_only = [msg for msg, _caller in collected]
    # Append to INTERACTIONS while avoiding immediate duplicates
    for msg in messages_only:
        if not INTERACTIONS or INTERACTIONS[-1] != msg:
            INTERACTIONS.append(msg)
    return collected