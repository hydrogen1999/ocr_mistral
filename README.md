# Mistral OCR Service

A service that consumes PDF files from Kafka, processes them using Google Document AI's OCR capabilities, embeds the text in Pinecone, generates a summary, and publishes the results back to Kafka.

## Overview

This project implements a document processing pipeline that:

1. Consumes messages from Kafka containing document information
2. Downloads the document from MinIO storage
3. Processes the document using Google Document AI for OCR and entity extraction
4. Saves the OCR result as a text file and uploads it to MinIO
5. Embeds the OCR text in Pinecone for vector search capabilities
6. Summarizes the document content using a language model
7. Publishes the structured results back to Kafka

## Prerequisites

- Python 3.10 or higher
- Kafka server
- MinIO server
- Google Cloud account with Document AI enabled
- OpenAI API key for embedding and summarization
- Pinecone account and index

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
# MinIO Configuration
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_minio_secret_key
MINIO_ENDPOINT=your_minio_endpoint
BUCKET_NAME_RAW=your_bucketname_raw
BUCKET_NAME_OCR=your_bucketname_ocr
NAMESPACE=your_minio_namespace

# Kafka Configuration
KAFKA_HOST=your_kafka_host
KAFKA_TOPIC=your_kafka_topic

# Google Cloud Configuration
GOOGLE_CREDENTIALS_TYPE=service_account
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_PRIVATE_KEY_ID=your_private_key_id
GOOGLE_PRIVATE_KEY=your_private_key
GOOGLE_CLIENT_EMAIL=your_client_email
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_X509_CERT_URL=your_client_x509_cert_url
GOOGLE_PROCESSOR_ID=your_processor_id
GOOGLE_PROCESSOR_VERSION_ID=your_processor_version_id

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
```

## Configuration

The application uses environment variables for configuration. You can also customize configuration by modifying the following files:

- `apps/service/Minio/MinioEngine.py`: MinIO connection settings
- `apps/service/Kafka/kafka_engine.py`: Kafka connection settings
- `apps/core/processor.py`: Message processing logic

### MinIO Security Configuration

By default, the application uses an insecure (HTTP) connection to MinIO. To use HTTPS:

1. Initialize the MinIO client with `secure=True`:

```python
minio_engine = MinioEngine(secure=True)
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mistral-ocr
```

2. Create a virtual environment:
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Start the document processing service:

```bash
# Make sure the virtual environment is activated
python main.py
```

To test the service with a sample file, use the SubServer:

```bash
python SubServer.py
```

To stop the service, press `Ctrl+C`. When you're done working with the project, deactivate the virtual environment:

```bash
deactivate
```

### Input Message Format

The service expects Kafka messages in the following JSON format:

```json
{
  "transID": "transaction-id",
  "raw_id": "raw-document-id", 
  "raw_url": "/bucket-name/namespace/file.pdf",
  "source": "source-name",
  "extra_data": {}
}
```

#### Raw URL Format

The `raw_url` field follows this format: `/<bucket-name>/<object-path>`. The system supports URL-encoded slashes (%2F) in the object path. For example:

- Standard format: `/raw-data/masvn/document.pdf`
- With URL-encoded slashes: `/raw-data/masvn%2Ffolders%2Fdocument.pdf`

### Output Message Format

After document processing, the service will publish results in the following format:

```json
{
  "transID": "transaction-id",
  "raw_id": "raw-document-id", 
  "raw_url": "/bucket-name/namespace/file.pdf",
  "ocr_url": "/ocr-bucket-name/namespace/ocr_result.txt",
  "source": "source-name",
  "title": "Document Title",
  "summary": "Document summary text...",
  "type": 1,
  "subject": "Document subject",
  "country": "Country",
  "industry": "Industry",
  "asset": "Asset",
  "subtype": 1,
  "symbols": [
    {
      "s": "AAPL",
      "recommend": 12.3,
      "target": 15.7
    }
  ],
  "extra_data": {}
}
```

## Project Structure

The project follows a modular architecture:

- `main.py`: Application entry point and orchestrator
- `SubServer.py`: Utility script for testing the service
- `apps/`: Application code
  - `api/`: API endpoints
  - `config/`: Configuration and logging
  - `core/`: Core processing logic
    - `processor.py`: Main logic for document processing and workflow coordination
  - `models/`: Data models
    - `schemas.py`: Pydantic models for message validation
  - `service/`: Service integrations
    - `Embedding/`: Embedding service
      - `pipecone_vectorstore_engine.py`: Pinecone integration for vector storage
    - `GoogleCloudService/`: Google Cloud integration
      - `GoogleCloudService.py`: Document AI integration for OCR and entity extraction
    - `Kafka/`: Kafka integration
      - `kafka_engine.py`: Kafka consumer/producer operations
    - `Llm/`: Language model integration
      - `llm_core.py`: LLM integration for summarization and information extraction
    - `Minio/`: MinIO integration
      - `MinioEngine.py`: Object storage operations
  - `utils/`: Utility modules
    - `prompts/`: LLM prompts
      - `DETERMINE_RECOMMENDATION.py`: Prompt to determine if document is a recommendation
      - `EXTRACT_INFORMATION.py`: Prompt to extract structured information
      - `SUMMARY.py`: Prompt to summarize document

## Key Features

- Asynchronous processing using asyncio for non-blocking operations
- Parallel processing of OCR, embedding, and summarization
- Support for different document types (PDF, text files, Word documents)
- URL-encoded path support for MinIO object paths
- Advanced entity extraction using Google Document AI
- Vector embedding for semantic search
- LLM-based summarization and information extraction
- Clean shutdown with graceful task completion

## Development

The project uses Pydantic for message validation. To modify message formats, update the models in `apps/models/schemas.py`.

To add support for new document types, extend the processing methods in `apps/core/processor.py`.

## Troubleshooting

### Common Issues

1. **Kafka Connection Issues**: Ensure Kafka server is running and accessible at the configured host.
2. **MinIO Access Issues**: 
   - Verify MinIO credentials and endpoint are correct
   - Check if you need to use secure=True (HTTPS) or secure=False (HTTP)
3. **Google Cloud Authentication Issues**: 
   - Verify that your service account credentials are correct
   - Ensure the service account has access to Document AI
4. **OpenAI API Issues**: Verify your API key is valid and has sufficient quota
5. **Pinecone Issues**: Verify your API key and index name are correct

### Logs

Check the application logs for detailed error information.

