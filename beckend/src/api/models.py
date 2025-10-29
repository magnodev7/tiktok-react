"""Modelos Pydantic reaproveitados entre roteadores."""

from __future__ import annotations

from typing import List, Optional, Union

import datetime as dt

from pydantic import BaseModel, Field, field_validator


class ScheduleUpdate(BaseModel):
    schedules: List[str]


class RescheduleVideoRequest(BaseModel):
    new_datetime: dt.datetime

    @field_validator("new_datetime", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, dt.datetime):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("new_datetime não pode ser vazio")
            try:
                return dt.datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Formato inválido. Use ISO 8601, ex: 2025-10-28T16:45") from exc
        raise ValueError("new_datetime deve ser datetime ou string ISO 8601")


class PostNowRequest(BaseModel):
    video_path: str
    account: str


class TikTokAccountCreate(BaseModel):
    account_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    cookies_data: Optional[Union[dict, list]] = None
    is_default: bool = False

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Nome da conta não pode ser vazio")
        if not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError("Nome da conta deve conter apenas letras, números, _ e -")
        return v.strip()

    @field_validator("display_name", "description")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            return None
        return v.strip() if v else None

    @field_validator("cookies_data", mode="before")
    @classmethod
    def validate_cookies(cls, v):
        if v in (None, "", {}, []):
            return None
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                import json

                parsed = json.loads(v)
                if isinstance(parsed, (dict, list)):
                    return parsed
                raise ValueError("Cookies devem ser um objeto JSON ou array")
            except json.JSONDecodeError:
                raise ValueError("Cookies devem ser um JSON válido") from None
        if isinstance(v, (dict, list)):
            return v
        raise ValueError("Cookies devem ser um objeto JSON ou array")


class TikTokAccountUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    cookies_data: Optional[Union[dict, list]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class TikTokAccountPublic(BaseModel):
    id: int
    account_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    cookies_data: Optional[Union[dict, list]] = None
    is_active: bool = True
    is_default: bool = False
    total_uploads: int = 0
    last_upload: Optional[dt.datetime] = None
    created_at: Optional[dt.datetime] = Field(default=None)
    updated_at: Optional[dt.datetime] = Field(default=None)
    profile_pic: Optional[str] = None
    profile_pic_updated_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True


class TikTokPinVideoRequest(BaseModel):
    video_id: str

    @field_validator("video_id")
    @classmethod
    def validate_video_id(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("video_id não pode ser vazio")
        return value
