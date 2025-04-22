from langchain_openai import ChatOpenAI
from apps.utils.prompts.EXTRACT_INFORMATION import (
    EXTRACT_INFORMATION_OTHER_PROMPT,
    EXTRACT_INFORMATION_RECOMMENDATION_PROMPT,
)
from apps.models.schemas import ExtractInformationResponse
from apps.utils.prompts.DETERMINE_RECOMMENDATION import DETERMINE_RECOMMENDATION_PROMPT
from apps.utils.prompts.SUMMARY import SUMMARIZE_PROMPT
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from apps.config.logging import logger
from apps.config.settings import (
    OPENAI_API_KEY,
)


class LLMCore:
    def __init__(self, model_name: str = "gpt-4o-mini", **kwargs):
        self.model = ChatOpenAI(
            model=model_name,
            temperature=0,
            max_retries=2,
            api_key=OPENAI_API_KEY,
            model_kwargs={"response_format": {"type": "json_object"}},
            **kwargs,
        )
        self.parser = JsonOutputParser()

    async def extract_information(self, ocr_response) -> dict:
        # Determine recommendation or not
        determine_recommendation_prompt = PromptTemplate.from_template(
            DETERMINE_RECOMMENDATION_PROMPT,
        )
        chain = determine_recommendation_prompt | self.model | self.parser
        determine_recommendation = await chain.ainvoke(
            {"document": "".join([page.markdown for page in ocr_response.pages])}
        )
        is_recommendation = determine_recommendation["is_recommendation"]

        extract_information_prompt = (
            EXTRACT_INFORMATION_RECOMMENDATION_PROMPT
            if is_recommendation
            else EXTRACT_INFORMATION_OTHER_PROMPT
        )

        # Extract information
        first_two_pages = "".join([page.markdown for page in ocr_response.pages[:2]])
        last_page = ocr_response.pages[-1].markdown
        extract_information_prompt = PromptTemplate.from_template(
            extract_information_prompt,
        )
        chain = extract_information_prompt | self.model | self.parser
        response = await chain.ainvoke(
            {"first_two_pages": first_two_pages, "last_page": last_page}
        )
        response["type"] = 1 if is_recommendation else 2
        logger.info(f"Extract information: {response}")
        return ExtractInformationResponse(**response).model_dump()

    async def summarize_document(self, ocr_response: str) -> str:
        content = "".join([page.markdown for page in ocr_response.pages])
        summarize_prompt = PromptTemplate.from_template(
            SUMMARIZE_PROMPT,
        )
        chain = summarize_prompt | self.model | self.parser
        response = await chain.ainvoke({"report_content": content})
        return response["summary"]
