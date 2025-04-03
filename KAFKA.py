from kafka import KafkaConsumer, KafkaProducer
from config_loader import ConfigLoader
from loguru import logger

class KafkaEngine:
    def __init__(self, host=None, topic=None):
        if host is None or topic is None:
            config = ConfigLoader()
            kafka_config = config.get_kafka_config()
            
        host = host or kafka_config.get('host')
        topic = topic or kafka_config.get('topic')
        
        if not host or not topic:
            raise ValueError("Kafka host and topic must be provided either through parameters or config file")
        
        self._topic = topic
        self._host = host
        
        logger.info(f"Initializing Kafka consumer with host={host}, topic={topic}")
        self._consumer = KafkaConsumer(topic, bootstrap_servers=host)
        self._producer = KafkaProducer(bootstrap_servers=host)

    @property
    def consumer(self):
        return self._consumer
    
    @property
    def producer(self):
        return self._producer
    
    @property
    def topic(self):
        return self._topic


