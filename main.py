import asyncio
from apps.config.logging import logger
from fastapi import FastAPI
from apps.core.processor import ProcessingEngine
from contextlib import asynccontextmanager
import uvicorn
from apps.api.router import api_router

processing_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start up
    global processing_engine
    processing_engine = ProcessingEngine()
    
    await processing_engine.kafka_engine.start()
    listen_task = asyncio.create_task(processing_engine.listen_and_process())
    yield
    # End - proper cleanup
    listen_task.cancel()
    await processing_engine.kafka_engine.close()
    await processing_engine.shutdown()
    
app = FastAPI(lifespan=lifespan)    

# Include API router
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)