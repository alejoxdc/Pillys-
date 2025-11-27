from typing import TypedDict

class RutStatusDict(TypedDict):
    tin:str
    name:str
    check_digit:str
    status:str