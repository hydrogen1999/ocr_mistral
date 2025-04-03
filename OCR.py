from mistralai import Mistral
import os
from dotenv import load_dotenv
from datauri import DataURI
from loguru import logger

load_dotenv()

class OCREngine:
    def __init__(self):
        self.client  = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

    def ocr(self, file_url : str):
        
        logger.info(f"OCRing {file_url}")
        ocr_response = self.client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": file_url
            },
            include_image_base64=True
        )
        
        logger.info(f"Starting to save markdown file")
        self.__create_markdown_file(ocr_response)
        return ocr_response
    
    def __process_ocr_response(self, ocr_response):
        pass

    def __save_image(self, image):
        if not os.path.exists(f"images"):
            os.makedirs(f"images")
            
        parsed = DataURI(image.image_base64)
        with open(f"images/{image.id}", "wb") as file:
            file.write(parsed.data)

    def __create_markdown_file(self, ocr_response, output_filename = "output_scanned.md"):
        with open(output_filename, "wt") as f:
            for page in ocr_response.pages:
                f.write(page.markdown)
                for image in page.images:
                    self.__save_image(image)



