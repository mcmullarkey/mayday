"""Room codes: the four letters on the TV that let phones in the room join (ADR-0003).

Contains the RoomCode type and a generator that takes its randomness as an argument.
Does not: decide when a code is issued or check a phone's guess (see lobby).
"""

import random
from typing import NewType

RoomCode = NewType("RoomCode", str)

# No I, L or O: on a TV across the room they read as 1, 1 and 0.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ"

# Codes nobody wants shouted across a party in front of their aunt.
BLOCKED = frozenset(
    {"ANUS", "ARSE", "CRAP", "CUNT", "DAMN", "DYKE", "FAGS", "FUCK", "FUKK", "PUBE", "SEXY", "TWAT", "WANK"}
)


def new_room_code(rng: random.Random) -> RoomCode:
    while True:
        code = "".join(rng.choice(ALPHABET) for _ in range(4))
        if code not in BLOCKED:
            return RoomCode(code)
