### OCR engine will be used to OCR the file and return the result

from mistralai import Mistral
import os
from dotenv import load_dotenv
from datauri import DataURI
from log_config import logger
import datetime

load_dotenv()

class OCREngine:
    def __init__(self):
        try:
            api_key = os.getenv('MISTRAL_API_KEY', None)
            if not api_key:
                raise ValueError("MISTRAL_API_KEY environment variable not set")
            self.client = Mistral(api_key=api_key)
        except Exception as e:
            logger.error(f"Error initializing Mistral client: {str(e)}")
            raise

    async def ocr(self, file_url : str) -> bool:
        try:
            logger.info(f"OCRing {file_url}")
            ocr_response = await self.client.ocr.process_async(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": file_url
                },
                include_image_base64=True
            )
            
            logger.info(f"Starting to save markdown file")
            self.__create_markdown_file(ocr_response, file_url)
            return True
        except Exception as e:
            logger.error(f"Error during OCR processing: {str(e)}")
            return False
    
    def __process_ocr_response(self, ocr_response):
        pass

    def __save_image(self, image, output_dir):
        try:
            images_dir = os.path.join(output_dir, "images")
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
                
            parsed = DataURI(image.image_base64)
            image_path = os.path.join(images_dir, image.id)
            with open(image_path, "wb") as file:
                file.write(parsed.data)
        except Exception as e:
            logger.error(f"Error saving image {image.id}: {str(e)}")

    def __create_markdown_file(self, ocr_response, file_url=None):
        try:
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            pdf_name = 'document'
            if file_url:
                pdf_name = os.path.splitext(os.path.basename(file_url))[0]
                
            output_dir = f"{current_time}_{pdf_name}"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            output_filename = os.path.join(output_dir, "output_scanned.md")
            with open(output_filename, "wt") as f:
                for page in ocr_response.pages:
                    f.write(page.markdown)
                    for image in page.images:
                        self.__save_image(image, output_dir)
            logger.info(f"OCR results saved to {os.path.abspath(output_dir)}")
            return output_dir
        except Exception as e:
            logger.error(f"Error creating markdown file: {str(e)}")
            return None



