from OCR import OCREngine
from KAFKA import KafkaEngine
from MINIO import MinioEngine
from loguru import logger
import os

ocr_engine = OCREngine()
kafka_engine = KafkaEngine().consumer
minio_engine = MinioEngine()

def process_pdf(file_url):
    logger.info(f"Processing PDF file: {file_url}")
    ocr_result = ocr_engine.ocr(file_url)
    return ocr_result

def process_text_file(file_url, file_extension):
    logger.info(f"Processing text file ({file_extension}): {file_url}")
    # Logic to process text file
    return None

def process_doc_file(file_url):
    logger.info(f"Processing document file: {file_url}")
    # Logic to process document file
    return None

if __name__ == "__main__":
    latest_message = ""
    while True:
        messages = kafka_engine.poll(timeout_ms=1000)
        logger.info(messages)
        
        # Get kafka signal
        if messages:
            records = list(messages.values())[0]
            current_record = records[-1]
            if latest_message != current_record.value:    
                logger.info(f"Received message: {current_record.value}")
                
                # Get file from minio
                full_path = current_record.value.decode('utf-8')
                object_name = full_path.split('/')[-1] 
                response = minio_engine.get_object(bucket_name="test", object_name=object_name)
                
                download_url = minio_engine.get_presigned_url(bucket_name="test", object_name=object_name)
                logger.info(f"Download URL: {download_url}")
    
                file_extension = os.path.splitext(object_name)[1].lower()
                
                if file_extension == ".pdf":
                    ocr_result = process_pdf(download_url)
                elif file_extension in [".txt", ".md"]:
                    text_content = process_text_file(download_url, file_extension)
                elif file_extension in [".doc", ".docx"]:
                    doc_content = process_doc_file(download_url)
                else:
                    logger.warning(f"Unsupported file extension: {file_extension}")
            
            latest_message = current_record.value
    
   
