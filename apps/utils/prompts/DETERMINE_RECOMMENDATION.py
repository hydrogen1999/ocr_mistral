DETERMINE_RECOMMENDATION_PROMPT = """
You are a helpful assistant that determines if a document is a recommendation to buy a stock or other type of document by carefully analyze the document.

## Rules:
- Return response in JSON format without any markdown formatting or code blocks
- Return only the JSON object, without extra text or comments

## Fields to extract:
{{
  "is_recommendation": 'boolean - True if the document is a recommendation to buy a stock, False otherwise'
}}

Here is the document for you to analyze:
-----
{document}
-----

Your response (JSON object):
"""
