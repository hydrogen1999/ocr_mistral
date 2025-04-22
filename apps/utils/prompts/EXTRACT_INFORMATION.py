EXTRACT_INFORMATION_RECOMMENDATION_PROMPT = """
You are a helpful assistant that extracts information from a given pages of a document report.

## Rules:
- Return response in JSON format without any markdown formatting or code blocks.
- Return only the JSON object, without extra text or comments.
- Extract all available information for the required fields.
- If information for a field is not available, use empty string for text fields or appropriate default values.
- For symbols, include all stock symbols mentioned with their recommendation and target prices.
- Format numbers as numeric values, not strings.
- Return only fields in output JSON format.

## Fields to extract:
{{{{
  "title": "string - The title of the report/document",
  "subject": "string - Document subject category (e.g., 'Company Analysis', 'Event & Sector', etc.)",
  "subtype": "integer - Document subtype (1=Buy, 2=Sell, 3=Hold, 4=Positive Outlook, 5=Other)",
  "symbols": [
    {{
      "s": "string - Stock symbol/ticker (e.g., 'FPT', 'HPG')",
      "recommend": "number - Recommended price",
      "target": "number - Target price"
    }}
  ]
}}}}

When extracting symbols, include all stock symbols mentioned with their recommendation prices and target prices.

Here is the first two pages and the last page of the document for you to extract information and determine the type of document:
----- First two pages -----
{first_two_pages}
-----

----- Last page -----
{last_page}
-----

Your response (JSON object):
"""


EXTRACT_INFORMATION_OTHER_PROMPT = """
You are a helpful assistant that extracts information from a given pages of a document report.

## Rules:
- Return response in JSON format without any markdown formatting or code blocks
- Return only the JSON object, without extra text or comments
- Extract all available information for the required fields
- If information for a field is not available, use empty string for text fields or appropriate default values
- Format numbers as numeric values, not strings
- Return only fields in output JSON format.

## Fields to extract:
{{{{
  "title": "string - The title of the report/document",
  "subject": "string - Document subject category (e.g., 'Company Analysis', 'Event & Sector', etc.)",
  "subtype": "integer - Document subtype (1=Buy, 2=Sell, 3=Hold, 4=Positive Outlook, 5=Other)",
}}}}

Here is the first two pages and the last page of the document for you to extract information and determine the type of document:
----- First two pages -----
{first_two_pages}
-----

----- Last page -----
{last_page}
-----

Your response (JSON object):
"""

