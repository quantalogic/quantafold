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


if __name__ == "__main__":
    sample = """
<response>
    <thought>
        <reasoning>
            Since previous attempts to search for the current Prime Minister of France have 
            encountered errors, I will retry using the Wikipedia search tool. This time, I will 
            ensure that the query is properly formatted and concise to avoid further issues.
        </reasoning>
        <to_do>
            <step>
                <name>search_wikipedia</name>
                <description><![CDATA[Search Wikipedia for the current Prime Minister of France]]></description>
                <reason><![CDATA[Wikipedia is a reliable source for current political information, making it suitable for answering this query.]]></reason>
                <depends_on_steps/>
            </step>
        </to_do>
        <done/>
    </thought>
    <action>
        <tool_name>SEARCH_WIKIPEDIA</tool_name>
        <reason><![CDATA[To find the most recent information about the Prime Minister of France]]></reason>
        <arguments>
            <arg>
                <name>query</name>
                <value><![CDATA[Prime Minister of France]]></value>
            </arg>
            <arg>
                <name>lang</name>
                <value><![CDATA]></value>
            </arg>
            <arg>
                <name>max_lines</name>
                <value><![CDATA[100]]></value>
            </arg>
        </arguments>
    </action>
</response>

"""

    response = ResponseParser.parse(sample)
    print(response)
