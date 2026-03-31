"""
DarkMatter Python SDK
Replay, fork, and verify any AI workflow.
pip install darkmatter
"""

from .client import DarkMatter, commit, pull, replay, fork, verify, export, search, diff, me
from .exceptions import DarkMatterError, AuthError, NotFoundError

__version__ = "0.1.0"
__all__ = [
    "DarkMatter",
    "commit", "pull", "replay", "fork", "verify", "export", "search", "diff", "me",
    "DarkMatterError", "AuthError", "NotFoundError",
]
