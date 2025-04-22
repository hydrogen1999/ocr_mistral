from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import documentai
from typing import Literal, Dict, Any, Union
from google.api_core.client_options import ClientOptions
from google.auth.transport.requests import Request
from google.cloud.documentai_v1 import types
from asgiref.sync import sync_to_async
import httpx
from apps.config.logging import logger
import time
from apps.config.settings import (
    OCR_RECOMMEND_PROCESSOR_ID,
    OCR_OTHER_PROCESSOR_ID,
    CLASSIFICATION_PROCESSOR_ID,
    CLASSIFICATION_PROCESSOR_VERSION_ID,
    SUMMARIZATION_PROCESSOR_ID,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GOOGLE_PROJECT_ID,
    GOOGLE_PRIVATE_KEY_ID,
    GOOGLE_PRIVATE_KEY,
    GOOGLE_CLIENT_EMAIL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_X509_CERT_URL,
    GOOGLE_UNIVERSE_DOMAIN,
    GOOGLE_CREDENTIALS_TYPE,
)
import asyncio
from io import BytesIO
import PyPDF2
from typing import List

load_dotenv()


class GoogleCloudService:
    credentials_info = {
        "type": GOOGLE_CREDENTIALS_TYPE,
        "project_id": GOOGLE_PROJECT_ID,
        "private_key_id": GOOGLE_PRIVATE_KEY_ID,
        "private_key": GOOGLE_PRIVATE_KEY,
        "client_email": GOOGLE_CLIENT_EMAIL,
        "client_id": GOOGLE_CLIENT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": GOOGLE_CLIENT_X509_CERT_URL,
        "universe_domain": GOOGLE_UNIVERSE_DOMAIN,
    }
    _CACHED_CREDENTIALS = None
    _CREDENTIALS_EXPIRY = 0
    _TOKEN_REFRESH_BUFFER = 300  # 5 minutes
    MAX_PAGES = 15

    def __init__(self, **kwargs):
        try:
            self._ocr_recommend_processor_id = kwargs.get(
                "ocr_recommend_processor_id", OCR_RECOMMEND_PROCESSOR_ID
            )
            self._ocr_other_processor_id = kwargs.get(
                "ocr_other_processor_id", OCR_OTHER_PROCESSOR_ID
            )

            self._classification_processor_id = kwargs.get(
                "classification_processor_id", CLASSIFICATION_PROCESSOR_ID
            )
            self._classification_processor_version_id = kwargs.get(
                "classification_processor_version_id",
                CLASSIFICATION_PROCESSOR_VERSION_ID,
            )
            self._summarization_processor_id = kwargs.get(
                "summarization_processor_id", SUMMARIZATION_PROCESSOR_ID
            )
            self.gemini_api_key = kwargs.get("gemini_api_key", GEMINI_API_KEY)
            self.gemini_model = kwargs.get("gemini_model", GEMINI_MODEL)

            for key, value in self.credentials_info.items():
                if value is None:
                    raise ValueError(f"{key} is not set")

            if (
                not self._ocr_recommend_processor_id
                or not self._classification_processor_id
                or not self._classification_processor_version_id
                or not self._summarization_processor_id
                or not self.gemini_api_key
                or not self.gemini_model
            ):
                raise ValueError(
                    "Processor ID or version ID or Gemini API key or Gemini model is not set"
                )
        except Exception as e:
            logger.error(f"Error initializing GoogleCloudService: {e}")
            raise e

    def get_credentials(self):
        """
        Get Google Cloud credentials with caching mechanism.

        Returns:
            service_account.Credentials: The Google Cloud credentials
        """
        current_time = int(time.time())
        if (
            self._CACHED_CREDENTIALS
            and self._CREDENTIALS_EXPIRY > current_time + self._TOKEN_REFRESH_BUFFER
        ):
            return self._CACHED_CREDENTIALS

        credentials = service_account.Credentials.from_service_account_info(
            self.credentials_info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        # Cache the credentials and set expiry time
        credentials.refresh(Request())
        self._CACHED_CREDENTIALS = credentials
        if hasattr(credentials, "expiry"):
            self._CREDENTIALS_EXPIRY = int(credentials.expiry.timestamp())
        else:
            self._CREDENTIALS_EXPIRY = current_time + 3600

        return credentials

    async def classify_document(
        self,
        document_content: Union[bytes, str],
        location: str = "us",
        mime_type: str = "application/pdf",
        processor_version_id: str = None,
    ) -> str:
        """Classify document content from OCR response

        Args:
            file (bytes): file content
            location (str, optional): Google Cloud location. Defaults to "us".
            mime_type (str, optional): mime type. Defaults to "application/pdf".

        """
        try:
            if mime_type == "application/pdf":
                pdf_file = BytesIO(
                    document_content
                    if isinstance(document_content, bytes)
                    else document_content.encode("utf-8")
                )
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)

                if total_pages > self.MAX_PAGES: 
                    pdf_writer = PyPDF2.PdfWriter()
                    for page_num in range(0, min(self.MAX_PAGES, total_pages)):
                        pdf_writer.add_page(pdf_reader.pages[page_num])

                    output_pdf = BytesIO()
                    pdf_writer.write(output_pdf)
                    output_pdf.seek(0)
                    document_content = output_pdf.getvalue()

            _credentials = await sync_to_async(self.get_credentials)()
            opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
            client = documentai.DocumentProcessorServiceClient(
                client_options=opts, credentials=_credentials
            )

            if processor_version_id or self._classification_processor_version_id:
                name = client.processor_version_path(
                    _credentials.project_id,
                    location,
                    self._classification_processor_id,
                    processor_version_id or self._classification_processor_version_id,
                )
            else:
                name = client.processor_path(
                    _credentials.project_id, location, self._classification_processor_id
                )

            # Create the raw document with text/plain mime type
            if isinstance(document_content, str):
                document_content = document_content.encode("utf-8")
            raw_document = documentai.RawDocument(
                content=document_content, mime_type=mime_type
            )
            request = documentai.ProcessRequest(
                name=name,
                raw_document=raw_document,
            )

            result = client.process_document(request=request)
            document = result.document

            # Select highest confidence classification
            max_confidence = 0
            document_type = None
            for entity in document.entities:
                if entity.confidence > max_confidence:
                    max_confidence = entity.confidence
                    document_type = entity.type_

            if document_type is None:
                raise ValueError("No document type found")
            return document_type
        except Exception as e:
            logger.error(f"Error in classify document: {e}")
            return None

    async def ocr_extract_text(
        self,
        file: bytes,
        doc_type: Literal["recommend", "other"],
        location: str = "us",
        mime_type: str = "application/pdf",
        threshold: float = 0.7,
        processor_version_id: str = None,
    ) -> Dict[str, Any]:
        """OCR extract text from a file

        Args:
            file (bytes): file content
            doc_type (Literal["recommend", "other"]): document type
            location (str, optional): location. Defaults to "us".
            mime_type (str, optional): mime type. Defaults to "application/pdf".
            threshold (float, optional): Confidence threshold for entities. Defaults to 0.7.

        Returns:
            Dict[str, Any]: Dictionary containing OCR content and extracted entities
        """
        try:
            if mime_type == "application/pdf":
                pdf_file = BytesIO(file)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)

                if total_pages > self.MAX_PAGES:
                    chunks = []
                    for start_page in range(0, total_pages, self.MAX_PAGES):
                        end_page = min(start_page + self.MAX_PAGES, total_pages)
                        chunks.append((start_page, end_page))

                    # Process asynchronously
                    tasks = [
                        self._process_pdf_chunk(
                            file,
                            doc_type,
                            location,
                            mime_type,
                            threshold,
                            processor_version_id,
                            page_range=chunk,
                        )
                        for chunk in chunks
                    ]

                    results = await asyncio.gather(*tasks)

                    # Merge results
                    merged_result = {"ocr_content": ""}
                    for result in results:
                        merged_result["ocr_content"] += result.get("ocr_content", "")
                        for key, value in result.items():
                            if key != "ocr_content":
                                if result.get(key) is None or result.get(key) == "":
                                    continue
                                if key not in merged_result:
                                    merged_result[key] = value
                                elif isinstance(merged_result[key], list):
                                    if isinstance(value, list):
                                        merged_result[key].extend(value)
                                    else:
                                        merged_result[key].append(value)
                                else:
                                    if key in merged_result:
                                        continue
                                    else:
                                        merged_result[key] = value

                    return merged_result

            return await self._process_single_document(
                file, doc_type, location, mime_type, threshold, processor_version_id
            )
        except Exception as e:
            logger.error(f"Error in OCR extract text: {str(e)}")
            return {}

    async def _process_pdf_chunk(
        self,
        file: bytes,
        doc_type: Literal["recommend", "other"],
        location: str,
        mime_type: str,
        threshold: float,
        processor_version_id: str,
        page_range: tuple,
    ) -> Dict[str, Any]:
        """Process a specific page range of a PDF file

        Args:
            file (bytes): The complete PDF file
            doc_type (Literal["recommend", "other"]): document type
            location (str): Google Cloud location
            mime_type (str): MIME type
            threshold (float): Confidence threshold for entities
            processor_version_id (str): Processor version ID
            page_range (tuple): Range of pages to process (start_page, end_page)

        Returns:
            Dict[str, Any]: OCR results for the specified page range
        """
        try:
            # Extract specified pages from the PDF
            start_page, end_page = page_range
            pdf_file = BytesIO(file)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Create a new PDF with only the specified pages
            pdf_writer = PyPDF2.PdfWriter()
            for page_num in range(start_page, end_page):
                pdf_writer.add_page(pdf_reader.pages[page_num])

            # Save the new PDF to a BytesIO object
            output_pdf = BytesIO()
            pdf_writer.write(output_pdf)
            output_pdf.seek(0)

            # Process the chunk
            return await self._process_single_document(
                output_pdf.getvalue(),
                doc_type,
                location,
                mime_type,
                threshold,
                processor_version_id,
            )
        except Exception as e:
            logger.error(f"Error processing PDF chunk {page_range}: {str(e)}")
            return {"ocr_content": ""}

    async def _process_single_document(
        self,
        file: bytes,
        doc_type: Literal["recommend", "other"],
        location: str,
        mime_type: str,
        threshold: float,
        processor_version_id: str,
    ) -> Dict[str, Any]:
        """Process a single document or document chunk

        Args:
            file (bytes): File content to process
            doc_type (Literal["recommend", "other"]): document type
            location (str): Google Cloud location
            mime_type (str): MIME type
            threshold (float): Confidence threshold for entities
            processor_version_id (str): Processor version ID

        Returns:
            Dict[str, Any]: OCR results
        """
        _credentials = await sync_to_async(self.get_credentials)()
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(
            client_options=opts, credentials=_credentials
        )

        # Create raw document
        raw_document = documentai.RawDocument(content=file, mime_type=mime_type)

        # Document type processor determination
        processor_id = None
        if doc_type == "recommend":
            processor_id = self._ocr_recommend_processor_id
        else:
            processor_id = self._ocr_other_processor_id

        if processor_version_id:
            name = client.processor_version_path(
                _credentials.project_id,
                location,
                processor_id,
                processor_version_id,
            )
        else:
            name = client.processor_path(
                _credentials.project_id, location, processor_id
            )

        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document,
        )

        # Process document
        operation = client.process_document(request=request)
        result = operation.document

        # Get fields
        entities_dict = {
            "ocr_content": result.text,
        }

        # Extract entities
        for entity in result.entities:
            if entity.confidence > threshold:
                if (
                    entity.type_ != "author"
                    and entity.type_ != "author_email"
                    or entity.type_ not in entities_dict
                ):
                    entities_dict[entity.type_] = entity.mention_text
                else:
                    if isinstance(entities_dict[entity.type_], list):
                        entities_dict[entity.type_].append(entity.mention_text)
                    else:
                        entities_dict[entity.type_] = [entity.mention_text]

        return entities_dict

    async def summarize_document(
        self, document_content: Union[bytes, str], location: str = "us", **kwargs
    ) -> str:
        """Summarize document content from OCR response

        Args:
            document_content (Union[bytes, str]): The document content (text or PDF bytes)
            max_length (int, optional): Maximum length of the summary. Defaults to None.
            location (str, optional): Google Cloud location. Defaults to "us".

        Returns:
            str: Summary of the document
        """
        try:
            _credentials = await sync_to_async(self.get_credentials)()
            opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
            client = documentai.DocumentProcessorServiceClient(
                client_options=opts, credentials=_credentials
            )
            
            

            name = client.processor_path(
                _credentials.project_id, location, self._summarization_processor_id
            )

            if isinstance(document_content, str):
                # Convert text to bytes
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"https://{location}-documentai.googleapis.com/v1/projects/{_credentials.project_id}/locations/{location}/processors/{self._summarization_processor_id}:process",
                        headers={"Authorization": f"Bearer {_credentials.token}"},
                        json={
                            "text": document_content,
                        },
                    )
                
                    # Process document
                    response.raise_for_status()
                    result = response.json()
                    return result["summary"]

            # Handle PDF content
            pdf_file = BytesIO(document_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            
            if total_pages <= self.MAX_PAGES:
                # Process PDF directly with Document AI
                raw_document = documentai.RawDocument(
                    content=document_content, mime_type="application/pdf"
                )
                
                request = documentai.ProcessRequest(
                    name=name,
                    raw_document=raw_document,
                )
                
                result = client.process_document(request=request)
                return result.document.summary
            else:
                # Process PDF in chunks of self.MAX_PAGES pages
                summaries = []
                for start_page in range(0, total_pages, self.MAX_PAGES):
                    end_page = min(start_page + self.MAX_PAGES, total_pages)
                    
                    # Create a new PDF with only the specified pages
                    pdf_writer = PyPDF2.PdfWriter()
                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    # Save the new PDF to a BytesIO object
                    output_pdf = BytesIO()
                    pdf_writer.write(output_pdf)
                    output_pdf.seek(0)
                    chunk_content = output_pdf.getvalue()
                    
                    # Process chunk with Document AI
                    raw_document = documentai.RawDocument(
                        content=chunk_content, mime_type="application/pdf"
                    )
                    
                    request = documentai.ProcessRequest(
                        name=name,
                        raw_document=raw_document,
                    )
                    
                    result = client.process_document(request=request)
                    for entity in result.document.entities:
                        if entity.type_ == "summary":
                            chunk_summary = entity.mention_text
                            summaries.append(chunk_summary)
                
                combined_summary = " ".join(summaries)
                return combined_summary
                
        except Exception as e:
            logger.error(f"Error summarize document: {e}")
            return ""
