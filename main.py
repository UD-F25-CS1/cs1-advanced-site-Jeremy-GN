from bakery import assert_equal
from drafter import *
from dataclasses import dataclass

@route
def index(state: State) -> Page:
    return Page(state, ["Hello World!"])


start_server(State())
