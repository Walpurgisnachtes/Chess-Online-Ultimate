

from __future__ import annotations

from typing import List, Callable, Optional
from random import shuffle, randrange, sample
from copy import deepcopy
from uuid import UUID, uuid4


class System:
    
    def __init__(self, name: str, id: str, desc: str) -> None:
        super().__init__()
        self.name: str = name
        self.id: str = id
        self.uuid: UUID = UUID(int=0)
        self.desc: str = desc
        self.cost: int = -1

    def __repr__(self) -> str:
        return f"<System {self.name!r} (id={self.id}) uuid={self.uuid}>"

    def __hash__(self) -> int:
        return hash(self.uuid)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, System):
            return NotImplemented
        return self.uuid == other.uuid