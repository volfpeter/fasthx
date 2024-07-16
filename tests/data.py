from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from pydantic_core import to_json


class User(BaseModel):
    name: str
    active: bool

    def __hash__(self) -> int:
        return hash((User, self.name, self.active))


billy = User(name="Billy Shears", active=True)
lucy = User(name="Lucy", active=True)

users: list[User] = [billy, lucy]


def get_random_number() -> int:
    return 4  # Chosen by fair dice roll.


DependsRandomNumber = Annotated[int, Depends(get_random_number)]

billy_html_header = "<h1>Billy Shears (active=True)</h1>"
billy_html_paragraph = "<p>Billy Shears (active=True)</p>"
billy_html_span = "<span>Billy Shears (active=True)</span>"
billy_json = billy.model_dump_json()
lucy_html = "<span>Lucy (active=True)</span>"
lucy_json = lucy.model_dump_json()
user_list_html = "<ul><li>Billy Shears (active=True)</li><li>Lucy (active=True)</li></ul>"
user_list_json = to_json(users).decode()
