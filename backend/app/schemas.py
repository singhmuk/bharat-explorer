from pydantic import BaseModel, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class Token(BaseModel):
    access_token: str
    is_premium: bool = False


class DestinationOut(BaseModel):
    id: int
    slug: str
    name: str
    state: str
    region: str
    summary: str
    best_season: str
    lat: float
    lng: float
    tags: list[str]
    model_config = {"from_attributes": True}


class DestinationDetail(DestinationOut):
    description: str


class VisitIn(BaseModel):
    slug: str
    action: str = Field(pattern="^(view|save|affiliate_click)$")


class ItineraryIn(BaseModel):
    prompt: str = Field(min_length=10, max_length=600)
    days: int = Field(ge=1, le=14, default=5)
