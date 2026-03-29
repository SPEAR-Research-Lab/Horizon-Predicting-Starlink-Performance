from dataclasses import dataclass
from typing import Callable

from .enums import Tables


@dataclass(frozen=True)
class LoadDataConfig:
    table: Tables
    get_query: Callable[[str, str], str]
    dataset_name: str
