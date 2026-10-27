from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.campus_access import require_admin
from app.database import get_db
from app.models.platform import PlatformSettings

router = APIRouter(prefix="/platform-settings", tags=["system"])


class SettingsBody(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}
    platform_name: str = Field(min_length=1, max_length=100)
    registration_open: bool

    @field_validator("platform_name")
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError("平台名称不能为空")
        return value.strip()


@router.get("", response_model=SettingsBody)
def read_settings(db: Session = Depends(get_db)):
    return db.get(PlatformSettings, 1)


@router.put("", response_model=SettingsBody)
def save_settings(body: SettingsBody, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(db, user)
    row = db.get(PlatformSettings, 1)
    row.platform_name = body.platform_name
    row.registration_open = body.registration_open
    db.commit()
    return row
