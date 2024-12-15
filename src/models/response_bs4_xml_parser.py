from bs4 import BeautifulSoup

from .response import Action, Response, Step, Thought


class ResponseBs4XmlParser:
    """Utility class to parse XML and create a Response object."""

    @staticmethod
    def _get_text_or_cdata(element) -> str:
        """Extract text from element, handling CDATA if present."""
        if not element:
            return ""
        return "".join(str(content) for content in element.contents).strip()

    @staticmethod
    def _parse_step(step_elem) -> Step:
        """Parse a single step element into a Step object."""
        if not step_elem.find("name") and not step_elem.find("n"):
            raise ValueError("Step name is mandatory")
        if not step_elem.find("description"):
            raise ValueError("Step description is mandatory")
        if not step_elem.find("reason"):
            raise ValueError("Step reason is mandatory")

        name = (step_elem.find("name") or step_elem.find("n")).get_text().strip()
        description = ResponseBs4XmlParser._get_text_or_cdata(
            step_elem.find("description")
        )
        reason = ResponseBs4XmlParser._get_text_or_cdata(step_elem.find("reason"))

        result = None
        result_elem = step_elem.find("result") or step_elem.find("r")
        if result_elem:
            result = ResponseBs4XmlParser._get_text_or_cdata(result_elem)

        depends_on_steps = []
        depends_elem = step_elem.find("depends_on_steps") or step_elem.find(
            "depends_on"
        )
        if depends_elem:
            depends_on_steps = [
                step_name.get_text().strip()
                for step_name in depends_elem.find_all("step_name")
            ]

        return Step(
            name=name,
            description=description,
            reason=reason,
            result=result,
            depends_on_steps=depends_on_steps,
        )

    @staticmethod
    def parse(xml_data: str) -> Response:
        """Parse XML string to create a Response object.

        Args:
            xml_data (str): XML string representation of the Response.

        Returns:
            Response: A Pydantic Response object.

        Raises:
            ValueError: If the XML data is malformed or cannot be converted into a Response.
        """
        try:
            soup = BeautifulSoup(xml_data, "xml")
            response_elem = soup.find("response")
            if not response_elem:
                raise ValueError("Missing response element")

            thought_elem = response_elem.find("thought")
            if not thought_elem or not thought_elem.text.strip():
                raise ValueError("Missing or empty thought element")

            # Parse thought into separate components
            thought_text = thought_elem.text.strip()
            thought = Thought(
                reasoning=thought_text,
                plan="",  # Default empty plan
                to_do=[],  # Default empty to_do list
                done=[]    # Default empty done list
            )

            # Parse answer if present
            final_answer = None
            answer_elem = response_elem.find("final_answer")
            if answer_elem:
                final_answer = answer_elem.text.strip()

            # Create and return Response object
            return Response(
                thought=thought,
                final_answer=final_answer
            )

        except Exception as e:
            raise ValueError(f"Error parsing XML data: {str(e)}") from e


# Example usage
if __name__ == "__main__":
    xml_example = """
    <x>
    XXX
    <response>
    <thought>
        <reasoning>Based on the analysis, the steps required are clear.</reasoning>
        <to_do>
            <step>
                <n>gather_data</n>
                <description>Collect relevant data from the database.</description>
                <reason>Data is necessary for the analysis.</reason>
                <r>Data gathered successfully.</r>
                <depends_on>
                    <step_name>initialize</step_name>
                </depends_on>
        </to_do>
        <done>
            <step>
                <n>initialize</n>
                <description>Initialize the database connection.</description>
                <reason>Connection required to gather data.</reason>
                <r>Database connection established.</r>
                <depends_on/>
            </step>
        </done>
    </thought>
    <action>
        <tool_name>data_collector</tool_name>
        <reason>Selected for its efficiency in gathering large data sets.</reason>
        <arguments>
            <arg>
                <name>database</name>
                <value>main_db</value>
            </arg>
            <arg>
                <name>limit</name>
                <value>100</value>
            </arg>
        </arguments>
    </action>
</response>"""

    try:
        response_obj = ResponseBs4XmlParser.parse(xml_example)
        print(response_obj.model_dump_json(indent=2))
    except ValueError as e:
        print(f"Error: {e}")
