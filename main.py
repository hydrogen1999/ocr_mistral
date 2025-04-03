### This main file will be acted like a main flow of OCR system

from OCR import OCREngine
from KAFKA import KafkaEngine
from MINIO import MinioEngine
from log_config import logger
import os
import sys
import asyncio
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor

# Global flag to signal shutdown for all threads
shutdown_flag = threading.Event()

# Init engines
try:
    logger.info("Initializing OCR engine")
    ocr_engine = OCREngine()
    
    logger.info("Initializing Kafka engine")
    kafka_engine = KafkaEngine()
    
    logger.info("Initializing MinIO engine")
    minio_engine = MinioEngine()
except Exception as e:
    logger.critical(f"Failed to initialize required components: {str(e)}")
    logger.critical("Application cannot start due to initialization errors")
    sys.exit(1)

# Task queue for async processing
task_queue = queue.Queue()

async def process_pdf(file_url):
    logger.info(f"Processing PDF file: {file_url}")
    result = await ocr_engine.ocr(file_url)
    logger.info(f"Completed OCR processing for {file_url}, success: {result}")
    return result

async def process_text_file(file_url, file_extension):
    logger.info(f"Processing text file ({file_extension}): {file_url}")
    # Logic to process text file
    return True

async def process_doc_file(file_url):
    logger.info(f"Processing document file: {file_url}")
    # Logic to process document file
    return True

def run_async_task(coro, object_name):
    """Run an async coroutine in the worker thread with shutdown handling"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create a task
        task = loop.create_task(coro)
        
        while not task.done() and not shutdown_flag.is_set():
            loop.run_until_complete(asyncio.sleep(0.1))
            
        if not task.done() and shutdown_flag.is_set():
            logger.info(f"Cancelling async task for {object_name} due to shutdown")
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                logger.info(f"Task for {object_name} was cancelled")
            except Exception as e:
                logger.error(f"Error cancelling task for {object_name}: {str(e)}")
        elif task.done():
            logger.info(f"Async task for {object_name} completed successfully")
            
        # Clean up
        loop.close()
    except Exception as e:
        logger.error(f"Error in async task for {object_name}: {str(e)}")

def worker_thread():
    """Worker thread to handle async processing tasks"""
    logger.info("Starting worker thread for async processing")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        while not shutdown_flag.is_set():
            try:
                # Get a task from the queue with a timeout
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:  # Sentinel value to exit
                        logger.info("Worker thread received exit signal")
                        break
                        
                    file_url, file_extension, object_name = task
                    logger.info(f"Processing task for {object_name} with extension {file_extension}")
                    
                    # Process based on file type
                    if file_extension == ".pdf":
                        coro = process_pdf(file_url)
                    elif file_extension in [".txt", ".md"]:
                        coro = process_text_file(file_url, file_extension)
                    elif file_extension in [".doc", ".docx"]:
                        coro = process_doc_file(file_url)
                    else:
                        logger.warning(f"Unsupported file extension: {file_extension}")
                        task_queue.task_done()
                        continue
                    
                    # Run the async task
                    executor.submit(run_async_task, coro, object_name)
                    task_queue.task_done()
                    
                except queue.Empty:
                    pass
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
                time.sleep(1)  # Avoid tight loop on error
                
    logger.info("Worker thread exiting")

if __name__ == "__main__":
    # Start worker thread for async processing
    worker = threading.Thread(target=worker_thread, daemon=True)
    worker.start()
    
    latest_message = ""
    try:
        while True:
            try:
                messages = kafka_engine.consumer.poll(timeout_ms=1000)
                logger.info(messages)
                
                # Get kafka signal
                if messages:
                    records = list(messages.values())[0]
                    current_record = records[-1]
                    if latest_message != current_record.value:    
                        logger.info(f"Received message: {current_record.value}")
                        
                        try:
                            # Get file from minio
                            full_path = current_record.value.decode('utf-8')
                            object_name = os.path.basename(full_path) 
                            response = minio_engine.get_object(bucket_name="test", object_name=object_name)
                            
                            if response:
                                download_url = minio_engine.get_presigned_url(bucket_name="test", object_name=object_name)
                                logger.info(f"Download URL: {download_url}")
            
                                file_extension = os.path.splitext(object_name)[1].lower()
                                
                                # Add task to queue for async processing
                                logger.info(f"Queueing {object_name} for async processing")
                                task_queue.put((download_url, file_extension, object_name))
                            else:
                                logger.error(f"Failed to get object {object_name} from Minio")
                        except Exception as e:
                            logger.error(f"Error handling Minio operations: {str(e)}")
                    
                    latest_message = current_record.value
            except Exception as e:
                logger.error(f"Error in Kafka message processing: {str(e)}")
    except KeyboardInterrupt:
        logger.info("Shutting down OCR service")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {str(e)}")
    finally:
        # Set shutdown flag to signal all threads to stop
        logger.info("Setting shutdown flag")
        shutdown_flag.set()
        
        # Signal worker thread to exit
        logger.info("Signaling worker thread to exit")
        task_queue.put(None)
        
        # Wait for worker thread to finish
        logger.info("Waiting for worker thread to exit")
        worker.join(timeout=10)
        if worker.is_alive():
            logger.warning("Worker thread didn't exit cleanly, proceeding with shutdown")
        else:
            logger.info("Worker thread exited cleanly")
        
        # Close Kafka connection
        if kafka_engine:
            logger.info("Closing Kafka connections")
            kafka_engine.close()
            logger.info("Kafka connections closed")
    
   
