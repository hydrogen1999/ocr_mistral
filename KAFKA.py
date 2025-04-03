### This is a Kafka engine that will be used to send and receive messages from Kafka

from kafka import KafkaConsumer, KafkaProducer
from config_loader import ConfigLoader
from log_config import logger

class KafkaEngine:
    def __init__(self, host=None, topic=None):
        try:
            if host is None or topic is None:
                try:
                    config = ConfigLoader()
                    kafka_config = config.get_kafka_config()
                    host = host or kafka_config.get('host')
                    topic = topic or kafka_config.get('topic')
                except Exception as e:
                    logger.error(f"Failed to load Kafka configuration: {str(e)}")
                    raise
            
            if not host or not topic:
                raise ValueError("Kafka host and topic must be provided either through parameters or config file")
            
            self._topic = topic
            self._host = host
            
            logger.info(f"Initializing Kafka consumer with host={host}, topic={topic}")
            self._consumer = KafkaConsumer(topic, bootstrap_servers=host)
            self._producer = KafkaProducer(bootstrap_servers=host)
        except Exception as e:
            logger.error(f"Error initializing Kafka: {str(e)}")
            self._consumer = None
            self._producer = None
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
        
    def close_consumer(self):
        try:
            if self._consumer:
                logger.info("Closing Kafka consumer")
                self._consumer.close()
                logger.info("Kafka consumer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka consumer: {str(e)}")
    
    def close_producer(self):
        try:
            if self._producer:
                logger.info("Closing Kafka producer")
                self._producer.close()
                logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {str(e)}")
            
    def close(self):
        self.close_consumer()
        self.close_producer()
        
    def __del__(self):
        self.close()


