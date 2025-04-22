import asyncio
import os
import json
import urllib.parse
from apps.config.logging import logger
from apps.models.schemas import IncomingKafkaMessage, KafkaMessageSerializer
from apps.service.Kafka.kafka_engine import KafkaEngine
from apps.service.Minio.MinioEngine import MinioEngine
from apps.service.GoogleCloudService.GoogleCloudService import GoogleCloudService
from apps.service.Llm.llm_core import LLMCore
import time
from io import BytesIO


class ProcessingEngine:
    def __init__(
        self,
        google_cloud_service=None,
        kafka_engine=None,
        minio_engine=None,
        llm_core=None,
    ):
        self.google_cloud_service = google_cloud_service or GoogleCloudService()
        self.kafka_engine = kafka_engine or KafkaEngine()
        self.minio_engine = minio_engine or MinioEngine()
        self.llm_core = llm_core or LLMCore()
        self.active_tasks = set()

    async def process_pdf(
        self, bucket_name: str, object_name: str, message_data: IncomingKafkaMessage
    ):
        """Process a PDF file

        Args:
            bucket_name (str): Bucket name
            object_name (str): Object name
            message_data (IncomingKafkaMessage): Message data

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Processing PDF file: {object_name}")
            trans_id = message_data.transID

            # Download the file
            file_response = self.minio_engine.get_object(object_name, bucket_name)
            if not file_response:
                logger.error(f"Failed to get file from MinIO: {object_name}")
                return False

            file_data = file_response.read()

            # Summarization
            summary_task = asyncio.create_task(
                self.google_cloud_service.summarize_document(
                    document_content=file_data,
                )
            )

            # Classification
            start_time = time.time()
            document_type = await self.google_cloud_service.classify_document(
                document_content=file_data,
            )
            end_time = time.time()
            logger.info(f"Classification completed in {end_time - start_time} seconds")
            logger.info(f"Document type: {document_type}")

            start_time = time.time()
            ocr_response = await self.google_cloud_service.ocr_extract_text(
                file=file_data, doc_type=document_type.lower()
            )
            end_time = time.time()
            logger.info(f"OCR extraction completed in {end_time - start_time} seconds")

            if ocr_response == {}:
                logger.error(f"OCR extraction failed for {object_name}")
                return False

            # Write OCR content to file
            ocr_content = ocr_response.get("ocr_content", "")
            ocr_file = BytesIO(ocr_content.encode("utf-8"))

            # Upload OCR file to Minio
            ocr_bucket = self.minio_engine.bucket_name_ocr
            self.minio_engine.ensure_bucket_exists(ocr_bucket)

            self.minio_engine.insert_file(
                bucket_name=ocr_bucket,
                object_name=object_name,
                file_data=ocr_file,
                content_type="text/plain",
            )

            ocr_url = f"/{ocr_bucket}/{object_name}"
            logger.info(f"OCR content uploaded to MinIO: {ocr_url}")

            # Wait for summary task to complete
            await summary_task

            # Get summary result
            summary = summary_task.result()
            logger.info(f"Summary generated successfully with length {len(summary)}")

            # Send to Kafka
            kafka_message = KafkaMessageSerializer(
                transID=trans_id,
                raw_id=message_data.raw_id,
                raw_url=message_data.raw_url,
                ocr_url=ocr_url,
                source=message_data.source,
                title=ocr_response.get("title", ""),
                summary=summary,
                type=1 if document_type == "recommend" else 2,
                subject=ocr_response.get("subject", ""),
                country="",
                industry="",
                asset="",
                subtype=ocr_response.get("subtype", ""),
                symbols=ocr_response.get("symbols", []),
                extra_data=message_data.extra_data,
            )
            await self.kafka_engine.send_message(kafka_message.model_dump())
            logger.info(
                f"Successfully send message to Kafka topic: {kafka_message.model_dump()['transID']}"
            )
            return True
        except Exception as e:
            logger.error(f"Error in process_pdf: {str(e)}")
            return False
        finally:
            # Remove task from active set when done
            self.active_tasks.discard(asyncio.current_task())

    async def process_text_file(self, file_url, file_extension, message_data):
        """Process a text or markdown file"""
        # Implement text file processing logic
        logger.info(f"Processing text file: {file_url} with extension {file_extension}")
        # TODO: Implement text file processing
        return True

    async def process_doc_file(self, file_url, message_data):
        """Process a Word document file"""
        # Implement doc file processing logic
        logger.info(f"Processing doc file: {file_url}")
        # TODO: Implement doc file processing
        return True

    def parse_raw_url(self, raw_url: str):
        """Parse raw_url to extract bucket and object names"""
        if raw_url.startswith("/"):
            raw_url = raw_url[1:]

        decoded_url = urllib.parse.unquote(raw_url)
        parts = decoded_url.split("/", 1)
        if len(parts) < 2:
            return None, raw_url
        return parts[0], parts[1]

    async def process_message(self, message_value: bytes):
        """Parse and process a message from Kafka"""
        try:
            # Decode message from bytes to string
            message_str = message_value.decode("utf-8")

            # Parse the JSON
            parsed_data = json.loads(message_str)

            # Validate message using Pydantic model
            message_data = None
            try:
                message_data = IncomingKafkaMessage(**parsed_data)
                logger.info(f"Message validated: {message_data.transID}")
            except Exception as e:
                logger.error(f"Message validation failed: {str(e)}")
                return

            # Parse raw_url
            raw_url = message_data.raw_url
            bucket_name, object_name = self.parse_raw_url(raw_url)
            if not bucket_name or not object_name:
                logger.error(
                    f"Could not parse bucket/object name from raw_url: {raw_url}"
                )
                return

            # Get download URL

            # Determine file type
            file_name = os.path.basename(object_name)
            file_extension = os.path.splitext(file_name)[1].lower()

            # Create and track the appropriate task
            if file_extension == ".pdf":
                task = asyncio.create_task(
                    self.process_pdf(bucket_name, object_name, message_data)
                )
                task.set_name(f"process-{file_name}")
                self.active_tasks.add(task)
            # elif file_extension in [".txt", ".md"]:
            #     task = asyncio.create_task(self.process_text_file(download_url, file_extension, message_data))
            #     task.set_name(f"process-{file_name}")
            #     self.active_tasks.add(task)
            # elif file_extension in [".doc", ".docx"]:
            #     task = asyncio.create_task(self.process_doc_file(download_url, message_data))
            #     task.set_name(f"process-{file_name}")
            #     self.active_tasks.add(task)
            else:
                logger.warning(f"Unsupported file extension: {file_extension}")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    async def listen_and_process(self):
        """Main Kafka polling loop"""
        latest_message = b""
        try:
            while True:
                async for record in self.kafka_engine.consumer:
                    message_value = record.value
                    if latest_message != message_value:
                        asyncio.create_task(self.process_message(message_value))
                        latest_message = message_value

                # Yield control to let other tasks run
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Kafka listener task cancelled, shutting down")
        except Exception as e:
            logger.error(f"Error in Kafka message polling loop: {str(e)}")
        finally:
            return

    async def shutdown(self):
        """Cleanly shut down processing"""
        # Wait for active tasks to complete
        if self.active_tasks:
            logger.info(
                f"Waiting for {len(self.active_tasks)} active tasks to complete"
            )
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
