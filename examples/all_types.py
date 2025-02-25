from argumentation import Argumentation, ArgumentationModel
from pydantic.dataclasses import dataclass
from typing import Union, Literal
from typing_extensions import Annotated


@dataclass
class Struct:
    a: str
    b: int
    c: float


class Args(ArgumentationModel):
    union: Annotated[Union[str, int], Argumentation(description="A string or int")]
    literal: Annotated[Literal["test"], Argumentation(description="A literal string")]
    enum: Annotated[
        Literal["test", "test2"], Argumentation(description="A enum of strings")
    ]
    str_and_int: Annotated[tuple[str, int], Argumentation(description="A tuple")]
    boolean: Annotated[bool, Argumentation(description="A boolean argument")]
    str_list: Annotated[list[str], Argumentation(description="A list of strings")]
    number: Annotated[int, Argumentation(description="A number")]
    dictionary: Annotated[dict[str, str], Argumentation(description="A dictionary")]
    data_structure: Annotated[
        Struct, Argumentation(description="An arbitrary data structure")
    ]


def main(args: Args):
    print(args)


if __name__ == "__main__":
    Argumentation.run(main)
