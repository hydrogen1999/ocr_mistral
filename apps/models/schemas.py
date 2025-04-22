from pydantic import BaseModel, Field
from typing import List, Optional, Union


class Symbol(BaseModel):
    s: str
    recommend: float
    target: float


class KafkaMessageSerializer(BaseModel):
    transID: str
    raw_id: str
    raw_url: str
    ocr_url: str
    source: str
    title: str
    summary: str
    type: int = Field(description="1=Khuyến nghị, 2=Other")
    subject: str
    country: str
    industry: str
    asset: str
    subtype: str = Field(description="Buy, Sell, Hold, Positive Outlook, Other")
    symbols: List[Symbol] = []
    extra_data: dict = {}


class IncomingKafkaMessage(BaseModel):
    transID: str
    raw_id: str
    raw_url: str
    source: str
    extra_data: dict = {}


class ExtractInformationResponse(BaseModel):
    title: str
    author: list[str] = []
    type: str = Field(description="Recommendation to buy a stock, Other")
    subject: str
    subtype: str = Field(
        description="Buy, Sell, Hold, Positive Outlook, Other"
    )
    symbols: List[Symbol] = []
