from pydantic import BaseModel, EmailStr, Field, field_validator

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator('password')
    @classmethod
    def validate_password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value

class UserRegister(UserLogin):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8)
