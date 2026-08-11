"""Fail-fast input error carrying a precise, actionable message.

Message shape: ``<location>: <what's wrong> -> <how to fix>`` so a non-technical
user sees exactly which row/value is bad and what to do about it.
"""
from __future__ import annotations


class InputError(Exception):
    """Raised for any bad input; stops processing before a file is written."""

    def __init__(self, location: str, problem: str, fix: str):
        self.location = location
        self.problem = problem
        self.fix = fix
        super().__init__(f"{location}: {problem} -> {fix}")
