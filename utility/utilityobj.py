from dataclasses import dataclass
from typing import List, Optional, Any

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Pagination:
    index: int
    limit: int
    has_previous: bool
    has_next: bool
    next_index: int
    prev_index: int


@dataclass_json
@dataclass
class ListResponse:
    data: List
    pagination: Optional[Pagination]


@dataclass_json
@dataclass
class FullListResponse:
    data: List


@dataclass_json
@dataclass
class SuccessResponse:
    status: int
    message: str


@dataclass_json
@dataclass
class ErrorResponse:
    status: int
    message: str


class DatabusPage:
    index = None
    offset = None
    limit = 10

    def __init__(self, *args):
        index = 1
        limit = 10
        if len(args) == 1:
            index = int(args[0].GET.get('page', 1))
            limit = int(args[0].GET.get('limit', 10))
        elif len(args) == 2:
            index = args[0]
            limit = args[1]
        self.__set(index, limit)

    def __set(self, index, limit):
        self.index = index
        self.limit = limit
        self.offset = (index - 1) * limit

    def get_index(self):
        return self.index

    def get_offset(self):
        return self.offset

    def get_query_limit(self):
        return self.offset + self.limit + 1
