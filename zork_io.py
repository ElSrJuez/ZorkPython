from zork_logging import game_log, system_log, game_log_json
import inspect

# redefine input( as zork_input( which is a wrapper that can be used to process input text before passing it to zork

# this is an object that collects all printed strings as a collection, adding an attribute with the name of the function that called zork_print(
_PRINT_CACHE = []

def zork_input(prompt=''):
    user_input = input(prompt)
    # Log the command as a game action
    game_log(user_input)
    message_collection = collect_printed_messages()
    # Here you can add any processing you want to do with user_input
    return user_input

def zork_print(message=""):
    print(message)
    # log printed messages if needed
    
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
    

def get_caller_name():
    """
    Returns the name of the function that called this function.
    """
    # inspect.stack() returns a list of frame records.
    # [0] is the current function (get_caller_name).
    # [1] is the function that called the current function (the caller).
    # .function (Python 3.5+ named tuple attribute) or [3] (tuple index in Python 2)
    # gets the function/method name from the frame record.

    
def collect_printed_messages():
    """
    Returns the collected printed messages and clears the cache.
    Each entry is a tuple of (caller_name, message).
    """
    global _PRINT_CACHE
    collected = _PRINT_CACHE[:]
    game_log_json({"printed_messages": collected})
    _PRINT_CACHE = []
    return collected