### This is a Minio engine that will be used to upload and download files from Minio

from minio import Minio
from config_loader import ConfigLoader
from log_config import logger
import os
from dotenv import load_dotenv

load_dotenv()


class MinioEngine:
    def __init__(self, endpoint=None, access_key=None, secret_key=None, secure=False):
        try:
            if endpoint is None:
                try:
                    config = ConfigLoader()
                    minio_config = config.get_minio_config()
                    endpoint = endpoint or minio_config.get("endpoint")
                except Exception as e:
                    logger.error(f"Failed to load MinIO configuration: {str(e)}")
                    raise

            access_key = access_key or os.environ.get("MINIO_ACCESS_KEY")
            secret_key = secret_key or os.environ.get("MINIO_SECRET_KEY")

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

    def list_objects(self, bucket_name, prefix="", recursive=True):
        try:
            objects = self.client.list_objects(
                bucket_name, prefix=prefix, recursive=recursive
            )
            return objects
        except Exception as e:
            logger.error(f"Error listing objects in bucket {bucket_name}: {e}")
            return []

    def get_object(self, bucket_name, object_name):
        try:
            return self.client.get_object(bucket_name, object_name)
        except Exception as e:
            logger.error(
                f"Error getting object {object_name} from bucket {bucket_name}: {e}"
            )
            return None

    def get_presigned_url(self, bucket_name, object_name):
        try:
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

    def insert_pdf(self, bucket_name: str, file_path: str):
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
                
            object_name = os.path.basename(file_path)
            result = self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type="application/pdf",
            )
            logger.info(f"Successfully uploaded {object_name} to {bucket_name}, etag: {result.etag}")
            return result
        except Exception as e:
            logger.error(
                f"Error inserting PDF file {os.path.basename(file_path)} into bucket {bucket_name}: {e}"
            )
            return None

    def __del__(self):
        # Clean up resources if needed
        logger.info("MinIO engine resources released")
