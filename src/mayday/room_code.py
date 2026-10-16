"""Room codes: the four letters on the TV that let phones in the room join.

Contains the RoomCode type and a generator that takes its randomness as an argument.
Does not: decide when a code is issued or check a phone's guess (that is the server's job).
"""

import random
from typing import NewType

RoomCode = NewType("RoomCode", str)

# No I, L or O: on a TV across the room they read as 1, 1 and 0.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ"


def new_room_code(rng: random.Random) -> RoomCode:
    return RoomCode("".join(rng.choice(ALPHABET) for _ in range(4)))
