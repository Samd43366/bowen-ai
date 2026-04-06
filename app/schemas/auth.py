from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=6)
    role: Optional[str] = "user"  # user or admin
    admin_secret: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str 

class TokenResponse(BaseModel):
    access_token: str
    token_type: str 
    message: Optional[str] = None
class SocialLoginRequest(BaseModel):
    firebase_id_token: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class ResendOTPRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2)
    role: Optional[str] = None
    level: Optional[str] = None
    hostel: Optional[str] = None
    metadata: Optional[dict] = None