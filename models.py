from pydantic import BaseModel
from fastapi import UploadFile


class User(BaseModel):
    name: str
    email: str

class JobCreateRequest(BaseModel):
    email: str
    file : UploadFile