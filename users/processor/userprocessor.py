from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class RegisterRequest:
    username: str
    email: str
    password: str
    institute_name: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


register_req_schema = marshmallow_dataclass.class_schema(RegisterRequest)()


@dataclass
class LoginRequest:
    username: str
    password: str


login_req_schema = marshmallow_dataclass.class_schema(LoginRequest)()


@dataclass_json
@dataclass
class UserResponse:
    id: int
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    institute_name: Optional[str]
    phone: Optional[str]
    role: int
    plan: str
    papers_used: int


@dataclass_json
@dataclass
class AuthResponse:
    access: str
    refresh: str
    user: UserResponse


@dataclass
class UpdateProfileRequest:
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    institute_name: Optional[str] = None


update_profile_req_schema = marshmallow_dataclass.class_schema(UpdateProfileRequest)()


@dataclass
class ChangePasswordRequest:
    current_password: str
    new_password: str


change_password_req_schema = marshmallow_dataclass.class_schema(ChangePasswordRequest)()
