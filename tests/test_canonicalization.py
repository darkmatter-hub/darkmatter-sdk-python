"""
Canonicalization must match DarkMatter's server exactly.

This SDK hashes the payload on the client and the server re-hashes it to
verify. That only works if both compute the same value from the same payload.
They did not.

`canonicalize` sorted object keys with Python's `sorted()`, which orders by code
point. The server sorts with JavaScript's `Array.prototype.sort`, which orders
by UTF-16 code unit, as RFC 8785 3.2.3 requires. Those agree across the whole
BMP and disagree above it: U+1F600 encodes to the surrogate pair D83D DE00, so
it sorts below U+FF01 in UTF-16 and above it by code point.

A payload with an emoji key therefore hashed one way here and another on the
server, and the commit was rejected as a hash mismatch by the service that told
the client to compute it. Nothing caught it because every payload anyone tested
had ASCII keys.

Run: python -m pytest tests/
"""

import json

from darkmatter.client import canonicalize, hash_payload


def test_astral_key_sorts_before_bmp_key():
    """U+1F600 must precede U+FF01: surrogate D83D is below FF01 in UTF-16."""
    out = canonicalize({"a": 1, "\U0001F600": "x", "！": "y"})
    assert out.index("\U0001F600") < out.index("！"), out


def test_matches_server_hash_for_astral_keys():
    """Pinned against DarkMatter's src/integrity.js for the same payload.

    If this changes, the SDK and the server no longer agree and every commit
    carrying such a payload will be flagged as a hash mismatch.
    """
    payload = {"a": 1, "\U0001F600": "x", "！": "y"}
    assert hash_payload(payload) == (
        "4cc8e16be75173c70537050af73064175e1f971eb5070aeb3384ef9cae5b36b6"
    ), hash_payload(payload)


def test_bmp_only_payloads_are_unchanged():
    """The fix must not move a key that was already ordered correctly.

    Code point and UTF-16 agree across the whole BMP, so every payload that
    existed before this change must still hash to the same value. These are
    pinned from the published 1.4.4 output.
    """
    cases = {
        '{"a":1,"b":2}': {"b": 2, "a": 1},
        '{"nested":{"y":2,"z":1}}': {"nested": {"z": 1, "y": 2}},
        # Non-ASCII is fine as long as it stays inside the BMP.
        '{"a":3,"é":1,"中":2}': {"é": 1, "中": 2, "a": 3},
    }
    for expected, payload in cases.items():
        assert canonicalize(payload) == expected, canonicalize(payload)


def test_input_key_order_does_not_change_the_hash():
    a = {"a": 1, "\U0001F600": "x", "！": "y"}
    b = {"！": "y", "\U0001F600": "x", "a": 1}
    assert hash_payload(a) == hash_payload(b)


def test_astral_in_values_is_unaffected():
    """Only key ordering was wrong. Values were always emitted raw."""
    assert canonicalize({"note": "café \U0001F600"}) == \
        json.dumps({"note": "café \U0001F600"}, ensure_ascii=False,
                   separators=(",", ":"))
