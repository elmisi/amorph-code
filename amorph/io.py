from __future__ import annotations

import sys
from typing import Any, List, Optional


class IOBase:
    def write(self, *vals: Any) -> None:  # stdout channel
        print(*vals)

    def read(self, prompt: Optional[str] = None) -> str:
        return input(prompt if prompt is not None else "")


class StdIO(IOBase):
    pass


class QuietIO(IOBase):
    def __init__(self) -> None:
        self.outputs: List[str] = []

    def write(self, *vals: Any) -> None:
        self.outputs.append(" ".join(str(v) for v in vals))

    def read(self, prompt: Optional[str] = None) -> str:
        # In quiet mode, avoid blocking: return empty string
        # Callers should convert as needed; for int() this will fail explicitly.
        return ""

