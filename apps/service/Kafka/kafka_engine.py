from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import os
from apps.config.logging import logger
import json
from apps.models.schemas import KafkaMessageSerializer, IncomingKafkaMessage
from pydantic import ValidationError
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from apps.config.settings import (
    KAFKA_HOST,
    KAFKA_TOPIC,
)


class KafkaEngine:
    def __init__(self, host=None, topic=None):
        try:
            if host is None or topic:
                try:
                    host = host or KAFKA_HOST
                    topic = topic or KAFKA_TOPIC
                except Exception as e:
                    logger.error(f"Failed to load Kafka configuration: {str(e)}")
                    raise

            if not host or not topic:
                raise ValueError(
                    "Kafka host and topic must be provided either through parameters or config file"
                )

            self._topic = topic
            self._host = host
            self._processed_messages = set()

            logger.info(f"Initializing Kafka with host={host}, topic={topic}")
            self._consumer = None
            self._producer = None
        except Exception as e:
            logger.error(f"Error initializing Kafka: {str(e)}")
            raise

    @property
    def consumer(self):
        return self._consumer

    @property
    def producer(self):
        return self._producer

    @property
    def topic(self):
        return self._topic

    async def start(self, refresh_interval: int = 500):
        try:
            # Ensure topic exists
            self.ensure_topic_exists()

            # Initialize producer
            self._producer = AIOKafkaProducer(bootstrap_servers=self._host)
            await self._producer.start()
            logger.info("Kafka producer started")

            # Initialize consumer
            self._consumer = AIOKafkaConsumer(
                self._topic,
                bootstrap_servers=self._host,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                auto_commit_interval_ms=refresh_interval,
            )
            await self._consumer.start()
            logger.info(
                f"Kafka consumer started with host={self._host}, topic={self._topic}, auto_offset_reset={refresh_interval}"
            )

            return True
        except Exception as e:
            logger.error(f"Error starting Kafka: {str(e)}")
            if self._producer:
                await self._producer.stop()
                self._producer = None
            if self._consumer:
                await self._consumer.stop()
                self._consumer = None
            return False

    async def close_consumer(self):
        try:
            if self._consumer:
                await self._consumer.stop()
                self._consumer = None
        except Exception as e:
            logger.error(f"Error closing Kafka consumer: {str(e)}")

    async def close_producer(self):
        try:
            if self._producer:
                await self._producer.stop()
                self._producer = None
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {str(e)}")

    async def close(self):
        """Close both Kafka consumer and producer"""
        await self.close_consumer()
        await self.close_producer()

    async def send_message(self, message_object: dict):
        try:
            await self._producer.send_and_wait(
                self._topic, json.dumps(message_object).encode("utf-8")
            )
            return True
        except ValidationError as e:
            logger.error(f"Validation error when sending embedding result: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending embedding result to Kafka: {str(e)}")
            return False

    def ensure_topic_exists(self):
        """Check if the Kafka topic exists and create it if it doesn't"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self._host, client_id="topic-checker"
            )

            # List existing topics
            existing_topics = admin_client.list_topics()

            # Create topic if it doesn't exist
            if self._topic not in existing_topics:
                logger.warning(f"Topic '{self._topic}' does not exist. Creating it...")
                topic_list = [
                    NewTopic(name=self._topic, num_partitions=1, replication_factor=1)
                ]
                admin_client.create_topics(new_topics=topic_list, validate_only=False)
                logger.info(f"Topic '{self._topic}' created successfully")
            else:
                logger.info(f"Topic '{self._topic}' already exists")

            # Close admin client
            admin_client.close()
            return True
        except TopicAlreadyExistsError:
            logger.info(f"Topic '{self._topic}' already exists")
            return True
        except Exception as e:
            logger.error(f"Error ensuring topic exists: {str(e)}")
            return False
