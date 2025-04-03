import yaml
from loguru import logger

class ConfigLoader:
    def __init__(self, config_path="config.yml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        try:
            with open(self.config_path, 'r') as config_file:
                return yaml.safe_load(config_file)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            return {}
    
    def get_minio_config(self):
        return self.config.get('server', {}).get('minio', {})
    
    def get_kafka_config(self):
        return self.config.get('server', {}).get('kafka', {})
    