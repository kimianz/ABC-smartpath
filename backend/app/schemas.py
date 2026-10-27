from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator

GuidedField=Literal["goal","audience","team_size","experience","format","timeline_weeks","budget_gbp","constraints"]

def normalize_format(value):
    if not isinstance(value,str): return value
    v=value.strip().lower()
    return {"in-person":"classroom","in person":"classroom","face-to-face":"classroom","hybrid":"blended","no preference":"any","either":"any","skip":"any","remote":"online","virtual":"online"}.get(v,v)

def normalize_audience(value):
    if not isinstance(value,str): return value
    v=value.strip().lower()
    return {'me':'individual','myself':'individual','just me':'individual','for me':'individual','for myself':'individual','my team':'team','our team':'team','us':'team'}.get(v,v)

class Requirements(BaseModel):
    model_config = ConfigDict(extra='forbid')
    goal: str | None = Field(None, max_length=1200)
    experience: Literal['beginner','intermediate','advanced'] | None = None
    audience: Literal['individual','team'] | None = None
    _audience=field_validator('audience',mode='before')(normalize_audience)
    team_size: int | None = Field(None, ge=1, le=10000)
    format: Literal['online','classroom','blended','any'] | None = None
    _format=field_validator('format',mode='before')(normalize_format)
    timeline_weeks: int | None = Field(None, ge=1, le=520)
    budget_gbp: float | None = Field(None, ge=0, le=10000000)
    skills: list[str] | None = Field(None, max_length=30)
    constraints: str | None = Field(None, max_length=1200)

class Message(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    requirements: Requirements | None = None

    guided_field: GuidedField | None = None
    skipped_fields: list[GuidedField] = Field(default_factory=list,max_length=8)
    intent: Literal['support'] | None = None

class Capture(BaseModel):
    session_id: str
    name: str = Field(min_length=1,max_length=150)
    email: EmailStr
    company: str = Field('',max_length=200)
    action: Literal['quote','consultation','enrol','email','support']
    message: str | None = Field(None,max_length=4000)
    service_consent: bool
    marketing_consent: bool = False

class LeadUpdate(BaseModel):
    status: Literal['new','contacted','booked','replied','opted_out','lost'] | None = None
    next_action: str | None = Field(None,max_length=1000)
    paid_booking: bool | None = None
    booking_value_gbp: float | None = Field(None,ge=0,le=10000000,allow_inf_nan=False)

class Draft(BaseModel):
    kind: Literal['follow_up','quote','confirmation']

class ManualDraft(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    kind: Literal['follow_up','quote','confirmation'] = 'follow_up'
    subject: str = Field(min_length=1,max_length=200,pattern=r'^[^\r\n]+$')
    body: str = Field(min_length=1,max_length=10000)

class Decision(BaseModel):
    action: Literal['approve','edit','reject']
    body: str | None = Field(None,min_length=1,max_length=10000)

class Reminder(BaseModel):
    due_at: str
