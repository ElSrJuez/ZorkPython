# zork_config.py
_config: dict = {}

def get_config_value(setting_name: str, default=None):
    """Retrieve a configuration value by name."""
    return _config.get(setting_name, default)
