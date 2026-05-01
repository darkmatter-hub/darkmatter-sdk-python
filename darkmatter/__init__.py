"""
DarkMatter Python SDK
Replay, fork, and verify any AI workflow.
pip install darkmatter
"""

from .client import DarkMatter, commit, pull, replay, fork, verify, export, search, diff, me, share, markdown, bundle, retention, create_hook, list_hooks, delete_hook, hook_deliveries
from .exceptions import DarkMatterError, AuthError, NotFoundError

__version__ = "1.4.1"
__all__ = [
    "DarkMatter",
    "commit", "pull", "replay", "fork", "verify", "export", "search", "diff", "me",
    "share", "markdown", "bundle", "retention",
    "create_hook", "list_hooks", "delete_hook", "hook_deliveries",
    "DarkMatterError", "AuthError", "NotFoundError",
]
