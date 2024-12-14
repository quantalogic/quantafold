from .response import Response
from .response_bs4_xml_parser import ResponseBs4XmlParser
from .response_xml_parser import ResponseXmlParser


class ResponseParser:
    """Parser that tries to parse using ResponseXmlParser, then falls back to ResponseBs4XmlParser."""

    @staticmethod
    def parse(xml_data: str) -> Response:
        """Parse XML string to create a Response object using available parsers.

        Args:
            xml_data (str): XML string representation of the Response.

        Returns:
            Response: A Pydantic Response object.

        Raises:
            ValueError: If parsing fails with both parsers.
        """
        try:
            # Try parsing with ResponseXmlParser
            return ResponseXmlParser.parse(xml_data)
        except ValueError:
            try:
                # Fallback to ResponseBs4XmlParser
                return ResponseBs4XmlParser.parse(xml_data)
            except ValueError as e:
                raise ValueError(
                    "Failed to parse XML data with available parsers."
                ) from e
