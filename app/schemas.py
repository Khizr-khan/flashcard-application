from pydantic import BaseModel
from typing import List, Dict, Optional

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True

# FlashCard schemas
class FlashCardBase(BaseModel):
    card: str
    definition: str

class FlashCardCreate(FlashCardBase):
    pass

class FlashCardResponse(FlashCardBase):
    id: int

    class Config:
        orm_mode = True
