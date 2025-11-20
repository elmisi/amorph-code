from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


class AmorphError(Exception):
    pass


@dataclass
class ErrorContext:
    """Context information for runtime errors."""
    path: str                           # AST path where error occurred
    call_stack: List[str]               # Function call stack
    line_in_canonical: Optional[int] = None
    surrounding_context: Optional[str] = None


class AmorphRuntimeError(AmorphError):
    """Runtime error with optional context."""

    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context

    def format_rich(self) -> str:
        """Format error with full context for display."""
        lines = [f"RuntimeError: {str(self)}"]

        if self.context:
            lines.append(f"  at {self.context.path}")

            if self.context.call_stack:
                lines.append("  Call stack:")
                for func in reversed(self.context.call_stack):
                    lines.append(f"    {func}")

            if self.context.surrounding_context:
                lines.append("  Context:")
                lines.append(f"    {self.context.surrounding_context}")

        return "\n".join(lines)


class AmorphValidationError(AmorphError):
    pass

