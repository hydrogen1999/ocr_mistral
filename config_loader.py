### This is a config loader that will be used to load the config from the config.yml file

import yaml
from log_config import logger

class ConfigLoader:
    def __init__(self, config_path="config.yml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        try:
            with open(self.config_path, 'r') as config_file:
                config = yaml.safe_load(config_file)
                if not config:
                    error_msg = f"Configuration file {self.config_path} is empty or has invalid format"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                return config
        except FileNotFoundError:
            error_msg = f"Configuration file not found: {self.config_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        except yaml.YAMLError as e:
            error_msg = f"Error parsing YAML configuration: {e}"
            logger.error(error_msg)
            raise yaml.YAMLError(error_msg)
    
    def get_minio_config(self):
        minio_config = self.config.get('server', {}).get('minio', {})
        if not minio_config:
            error_msg = "MinIO configuration is missing or empty in config file"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return minio_config
    
    def get_kafka_config(self):
        kafka_config = self.config.get('server', {}).get('kafka', {})
        if not kafka_config:
            error_msg = "Kafka configuration is missing or empty in config file"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return kafka_config
    