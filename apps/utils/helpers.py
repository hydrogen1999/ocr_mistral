import uuid
import os
from datetime import datetime
import shutil
from config.logging import logger


def create_markdown_file(ocr_content: str) -> tuple[str, str]:
    """_summary_

    Args:
        ocr_content (str): OCR content

    Returns:
        tuple: output_dir, md_filename
    """

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_id = uuid.uuid4()
    pdf_name = f"document_{doc_id}"

    output_dir = f"{current_time}_{pdf_name}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    md_filename = f"{pdf_name}_ocr.md"
    output_filepath = os.path.join(output_dir, md_filename)

    with open(output_filepath, "wt", encoding="utf-8", errors="replace") as f:
        f.write(ocr_content)

    logger.info(f"OCR results saved to {os.path.abspath(output_filepath)}")
    return (output_dir, md_filename)


def cleanup_temp_files(output_dir):
    """ Clean up temporary files

    Args:
        output_dir (str): output directory
    """
    try:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            logger.info(f"Cleaned up temporary files in {output_dir}")
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")


def create_markdown_file(ocr_content: str):
    """ Create a markdown file from OCR content

    Args:
        ocr_content (str): OCR content

    Returns:
        tuple: output_dir, md_filename
    """
    try:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        doc_id = uuid.uuid4()
        pdf_name = f"document_{doc_id}"

        output_dir = f"{current_time}_{pdf_name}"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        md_filename = f"{pdf_name}_ocr.md"
        output_filepath = os.path.join(output_dir, md_filename)

        with open(output_filepath, "wt", encoding="utf-8", errors="replace") as f:
            f.write(ocr_content)

        logger.info(f"OCR results saved to {os.path.abspath(output_filepath)}")
        return (output_dir, md_filename)
    except Exception as e:
        logger.error(f"Error creating markdown file: {str(e)}")
        return None
