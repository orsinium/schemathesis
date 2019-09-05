"""Provide strategies for given endpoint(s) definition."""
import json
from functools import partial
from typing import Callable

import attr
import hypothesis.internal.conjecture.utils as cu
import hypothesis.strategies as st
from hypothesis import given
from hypothesis_jsonschema import from_schema

from .schemas import Endpoint
from .types import Body, Headers, PathParameters, Query

# TODO. Better naming


@attr.s(slots=True, hash=False)
class Case:
    """A single test case parameters."""

    path: str = attr.ib()
    method: str = attr.ib()
    path_parameters: PathParameters = attr.ib()
    headers: Headers = attr.ib()
    query: Query = attr.ib()
    body: Body = attr.ib()

    def __hash__(self):
        serialize = partial(json.dumps, sort_keys=True)
        return hash(
            (
                self.path,
                self.method,
                serialize(self.path_parameters),
                serialize(self.headers),
                serialize(self.query),
                serialize(self.body),
            )
        )

    @property
    def formatted_path(self) -> str:
        # pylint: disable=not-a-mapping
        return self.path.format(**self.path_parameters)


def create_hypothesis_test(endpoint: Endpoint, test: Callable) -> Callable:
    """Create a Hypothesis test."""
    strategy = get_case_strategy(endpoint)
    return given(case=strategy)(test)


def get_case_strategy(endpoint: Endpoint) -> st.SearchStrategy:
    case_strategy = st.builds(
        Case,
        path=st.just(endpoint.path),
        method=st.just(endpoint.method),
        path_parameters=from_schema(endpoint.path_parameters),
        headers=from_schema(endpoint.headers),
        query=from_schema(endpoint.query),
        body=from_schema(endpoint.body),
    )

    produced = set()

    @st.composite
    def unique_case(draw):
        elements = cu.many(draw(st.data()).conjecture_data, min_size=1, max_size=100, average_size=50)  # type: ignore
        while elements.more():
            case = draw(case_strategy)
            if case not in produced:
                produced.add(case)
                return case
            break

        elements.reject()

    return unique_case()
