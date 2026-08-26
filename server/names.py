"""Generated scratch names: adjective-noun-4chars (§5.3)."""

from __future__ import annotations

import secrets

_ADJECTIVES = (
    "amber coral ember moss slate copper cedar ivory umber sage pearl "
    "indigo ochre flax linen frost dune pine smoke ivory".split()
)
_NOUNS = (
    "harbor lantern meadow orchard ridge harbor mill quay grove "
    "ledger folio atlas ledger kiln loom quay ridge mill".split()
)
_ALPHANUM = "abcdefghijklmnopqrstuvwxyz0123456789"


def generate_name() -> str:
    adj = secrets.choice(_ADJECTIVES)
    noun = secrets.choice(_NOUNS)
    suffix = "".join(secrets.choice(_ALPHANUM) for _ in range(4))
    return f"{adj}-{noun}-{suffix}"
