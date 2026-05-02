"""
DarkMatter Python SDK
Replay, fork, and verify any AI workflow.
pip install darkmatter-sdk
"""

from .client import (
    configure,
    commit, replay, fork, verify, diff, bundle, me, checkpoint,
    verify_local, generate_keypair, generate_customer_keypair,
    canonicalize, hash_payload, build_envelope, hash_envelope, compute_integrity_hash,
)
from .exceptions import DarkMatterError, AuthError, NotFoundError

__version__ = "1.4.2"
__all__ = [
    "configure",
    "commit", "replay", "fork", "verify", "diff", "bundle", "me", "checkpoint",
    "verify_local", "generate_keypair", "generate_customer_keypair",
    "canonicalize", "hash_payload", "build_envelope", "hash_envelope", "compute_integrity_hash",
    "DarkMatterError", "AuthError", "NotFoundError",
]
