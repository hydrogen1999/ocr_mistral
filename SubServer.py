### This is a subserver that will be used to be act like a client to send file to Kafka

from KAFKA import KafkaEngine
from MINIO import MinioEngine
kafka_engine = KafkaEngine()
producer = kafka_engine.producer
topic = kafka_engine.topic

minio_engine = MinioEngine()

pdf_path = "data/1599642928150-document.pdf"

if __name__ == "__main__":
    # while True:
    minio_engine.insert_pdf(bucket_name="test", file_path=pdf_path)
    future = producer.send(topic, pdf_path.encode("utf-8"))
    result = future.get(timeout=10)
    print("Message sent to Kafka:", result)
