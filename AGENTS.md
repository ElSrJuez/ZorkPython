# AGENTS.md

## Build, Lint, and Test Commands
- **Run the game:**
  ```bash
  python zork_expanded.py
  ```
- **Lint:**
  - No enforced linter, but code follows PEP8. Use `flake8` or `ruff` for style checks if desired.
- **Test:**
  - No automated tests present. Manual playtesting is required.

## Code Style Guidelines
- **Imports:**
  - Standard library imports first, then third-party, then local modules.
- **Formatting:**
  - 4 spaces per indentation level. Use PEP8 formatting.
- **Types:**
  - Use type hints for all function signatures and class attributes.
- **Naming:**
  - snake_case for variables and functions, PascalCase for classes, UPPER_CASE for constants.
- **Error Handling:**
  - Use try/except for error-prone code. Log errors using `system_log` or `game_log`.
- **Classes:**
  - Use `@dataclass` for data containers. Use `Enum` for enumerations.
- **Docstrings:**
  - Provide docstrings for all public classes and functions.
- **Other:**
  - Avoid direct dependencies in controller layers; use protocols/abstract interfaces.
  - Keep UI, logic, and AI orchestration separated.

*No Cursor or Copilot rules detected. Update this file if new conventions or tools are added.*
