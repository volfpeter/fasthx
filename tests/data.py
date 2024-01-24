from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from pydantic_core import to_json


class User(BaseModel):
    name: str
    active: bool


users: list[User] = [
    User(name="Billy Shears", active=True),
    User(name="Lucy", active=True),
]


def get_random_number() -> int:
    return 4  # Chosen by fair dice roll.


DependsRandomNumber = Annotated[int, Depends(get_random_number)]

html_user_list = "<ul><li>Billy Shears (active=True)</li><li>Lucy (active=True)</li></ul>"
json_user_list = to_json(users).decode()
