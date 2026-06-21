# `qstrader.utils`

## Overview

The `qstrader.utils` package currently provides a small terminal formatting helper for colored console output.

At present, the package consists of a single utility module:

- **Console Helpers (`console.py`)**: ANSI escape-sequence formatting for colored text.

---

## Package layout

```text
qstrader/utils/
├── __init__.py
└── console.py
```

`qstrader/utils/__init__.py` is empty, so imports are made directly from `qstrader.utils.console`.

---

## Console helpers (`console.py`)

**Source:** `qstrader/utils/console.py`

### Color constants

The module defines eight integer constants via `range(8)`:

- `BLACK = 0`
- `RED = 1`
- `GREEN = 2`
- `YELLOW = 3`
- `BLUE = 4`
- `MAGENTA = 5`
- `CYAN = 6`
- `WHITE = 7`

These values map to ANSI foreground color codes `30-37` through the transformation `30 + colour`.

### `string_colour`

```python
string_colour(text: str, colour: int = WHITE) -> str
```

Returns `text` wrapped in ANSI escape sequences for bright foreground color formatting.

#### Parameters

- `text: str` - The plain text to colorize.
- `colour: int = WHITE` - Color selector constant (typically one of `BLACK..WHITE`).

#### Return value

- `str` - ANSI-formatted string:

  ```text
  "\x1b[1;{30+colour}m" + text + "\x1b[0m"
  ```

  where:
  - `\x1b[` starts the ANSI control sequence,
  - `1` enables bright/bold intensity,
  - `{30+colour}` sets foreground color,
  - `m` terminates the style sequence,
  - `\x1b[0m` resets formatting.

#### Notes

- This function is pure (no side effects); it only returns a new string.
- Output renders as colored text only in terminals that support ANSI escape codes.
- The function does not validate `colour`; non-standard values still produce an ANSI code.

#### Example

```python
from qstrader.utils.console import GREEN, string_colour

msg = string_colour("Backtest complete", GREEN)
print(msg)
```

---

## Test coverage

**Source:** `tests/unit/utils/test_console.py`

`string_colour` is covered by parameterized tests asserting exact escape-sequence output, for example:

- `GREEN` -> `"\x1b[1;32m...\x1b[0m"`
- `BLUE` -> `"\x1b[1;34m...\x1b[0m"`
- `CYAN` -> `"\x1b[1;36m...\x1b[0m"`

---

## Quick reference

| Symbol | Type | Purpose |
|---|---|---|
| `BLACK..WHITE` | `int` constants | Enumerate ANSI foreground colors 30-37 via offset (`30 + colour`) |
| `string_colour(text, colour=WHITE)` | function | Wrap text with ANSI bright-color + reset escape sequences |

---

## Summary

`qstrader.utils.console` provides a minimal ANSI color-formatting helper for console messaging in scripts and backtests.
