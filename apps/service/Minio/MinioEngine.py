### This is a Minio engine that will be used to upload and download files from Minio

from minio import Minio
from apps.config.logging import logger
import os
from dotenv import load_dotenv
from io import BytesIO
from apps.config.settings import (
    BUCKET_NAME_OCR,
    BUCKET_NAME_RAW,
    NAMESPACE,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
)

load_dotenv()


class MinioEngine:
    bucket_name_ocr = BUCKET_NAME_OCR
    bucket_name_raw = BUCKET_NAME_RAW
    namespace = NAMESPACE

    def __init__(self, endpoint=None, access_key=None, secret_key=None, secure=False):
        try:
            if (
                not self.bucket_name_ocr
                or not self.bucket_name_raw
                or not self.namespace
            ):
                raise ValueError("Bucket name or namespace is not set")

            if endpoint is None:
                try:
                    endpoint = endpoint or MINIO_ENDPOINT
                except Exception as e:
                    logger.error(f"Failed to load MinIO configuration: {str(e)}")
                    raise

            access_key = access_key or MINIO_ACCESS_KEY
            secret_key = secret_key or MINIO_SECRET_KEY

            if not endpoint or not access_key or not secret_key:
                raise ValueError(
                    "MinIO endpoint, access_key, and secret_key must be provided either through parameters, config file, or environment variables"
                )

            logger.info(f"Initializing MinIO client with endpoint={endpoint}")
            self.client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )
        except Exception as e:
            logger.error(f"Error initializing MinIO client: {str(e)}")
            raise

    def list_buckets(self):
        try:
            buckets = self.client.list_buckets()
            return buckets
        except Exception as e:
            logger.error(f"Error listing buckets: {e}")
            return []

    def ensure_bucket_exists(self, bucket_name):
        buckets = self.list_buckets()
        bucket_exists = any(bucket.name == bucket_name for bucket in buckets)

        if not bucket_exists:
            logger.info(f"Bucket {bucket_name} does not exist, attempting to create it")
            try:
                self.client.make_bucket(bucket_name)
                logger.info(f"Successfully created bucket: {bucket_name}")
            except Exception as e:
                logger.error(f"Failed to create bucket {bucket_name}: {str(e)}")

    def list_objects(self, bucket_name, prefix="", recursive=True):
        try:
            objects = self.client.list_objects(
                bucket_name, prefix=prefix, recursive=recursive
            )
            return objects
        except Exception as e:
            logger.error(f"Error listing objects in bucket {bucket_name}: {e}")
            return []

    def get_pdf(self, object_name, bucket_name: str = None):
        self.ensure_bucket_exists(bucket_name)
        try:
            if not bucket_name:
                bucket_name = self.bucket_name_raw
            return self.client.get_object(bucket_name, object_name)
        except Exception as e:
            logger.error(
                f"Error getting object {object_name} from bucket {bucket_name}: {e}"
            )

    def get_object(self, object_name, bucket_name: str = None):
        self.ensure_bucket_exists(bucket_name)
        try:
            if not bucket_name:
                bucket_name = self.bucket_name_raw
            return self.client.get_object(bucket_name, object_name)
        except Exception as e:
            logger.error(
                f"Error getting object {object_name} from bucket {bucket_name}: {e}"
            )
            return None

    def get_presigned_url(self, object_name, bucket_name: str = None):
        self.ensure_bucket_exists(bucket_name)
        try:
            if not bucket_name:
                bucket_name = self.bucket_name_raw
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
            )
            return url
        except Exception as e:
            logger.error(
                f"Error generating presigned URL for {object_name} from bucket {bucket_name}: {e}"
            )
            return None

    def insert_pdf(self, file_path: str, bucket_name: str = None):
        self.ensure_bucket_exists(bucket_name)
        try:
            if not bucket_name:
                bucket_name = self.bucket_name_raw
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            object_name = f"{self.namespace}/{os.path.basename(file_path)}"
            result = self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type="application/pdf",
            )
            logger.info(
                f"Successfully uploaded {object_name} to {bucket_name}, etag: {result.etag}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Error inserting PDF file {os.path.basename(file_path)} into bucket {bucket_name}: {e}"
            )
            return None

    def insert_md(self, file_path: str, bucket_name: str = None):
        self.ensure_bucket_exists(bucket_name)
        try:
            if not bucket_name:
                bucket_name = self.bucket_name_ocr
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            object_name = f"{self.namespace}/{os.path.basename(file_path)}"
            result = self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type="text/markdown",
            )
            logger.info(
                f"Successfully uploaded {object_name} to {bucket_name}, etag: {result.etag}"
            )
            return f"{bucket_name}/{object_name}"
        except Exception as e:
            logger.error(
                f"Error inserting MD file {os.path.basename(file_path)} into bucket {bucket_name}: {e}"
            )
            return None

    def insert_file(
        self,
        file_data: BytesIO,
        bucket_name: str = None,
        object_name: str = None,
        content_type: str = None,
    ):
        self.ensure_bucket_exists(bucket_name)
        try:
            if not bucket_name:
                bucket_name = self.bucket_name_raw

            if (
                not object_name
                or not content_type
                or bucket_name is None
                or file_data is None
            ):
                raise ValueError(
                    "Object name, content type, bucket name, and file data must be provided"
                )

            # Make the file data seekable
            current_pos = file_data.tell()
            file_data.seek(0, 2)
            file_length = file_data.tell()
            file_data.seek(0)

            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                content_type=content_type,
                length=file_length,
            )

            # Restore original position
            file_data.seek(current_pos)

            logger.info(
                f"Successfully uploaded {object_name} to {bucket_name}, etag: {result.etag}"
            )
            return f"{bucket_name}/{object_name}"
        except Exception as e:
            logger.error(
                f"Error inserting file {object_name} into bucket {bucket_name}: {e}"
            )
            return None

    def __del__(self):
        logger.info("MinIO engine resources released")
