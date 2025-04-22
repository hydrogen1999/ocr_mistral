from fastapi import APIRouter, HTTPException, Depends, status
from apps.config.logging import logger

router = APIRouter()

@router.post("/query")
async def query(query: str):
    pass
