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
    def _parse_arguments(action_elem) -> dict:
        """Parse arguments from action element."""
        arguments = {}
        if not action_elem:
            return arguments

        args_elem = action_elem.find("arguments")
        if not args_elem:
            return arguments

        # Parse direct argument children (argument1, argument2, etc.)
        for arg in args_elem.children:
            if arg.name and arg.string:  # Only process actual elements with content
                arguments[arg.name] = arg.string.strip()

        return arguments

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
                done=[],  # Default empty done list
            )

            # Parse answer if present
            final_answer = None
            answer_elem = response_elem.find("final_answer")
            if answer_elem:
                final_answer = answer_elem.text.strip()

            # Check if this is a final answer format
            final_answer_elem = response_elem.find("final_answer")
            if final_answer_elem:
                return Response(
                    thought=Thought(
                        reasoning=ResponseBs4XmlParser._get_text_or_cdata(thought_elem),
                        to_do=[],
                        done=[],
                    ),
                    final_answer=ResponseBs4XmlParser._get_text_or_cdata(
                        final_answer_elem
                    ),
                )

            # Otherwise parse the full format with action
            action_elem = response_elem.find("action")
            if not action_elem:
                raise ValueError("Missing action element")

            # Parse to_do and done steps
            to_do_steps = []
            done_steps = []

            to_do_container = thought_elem.find("to_do")
            if to_do_container:
                to_do_steps = [
                    ResponseBs4XmlParser._parse_step(step)
                    for step in to_do_container.find_all("step")
                ]

            done_container = thought_elem.find("done")
            if done_container:
                done_steps = [
                    ResponseBs4XmlParser._parse_step(step)
                    for step in done_container.find_all("step")
                ]

            # Create action object
            action = Action(
                step_name=action_elem.find("step_name").get_text().strip(),
                tool_name=action_elem.find("tool_name").get_text().strip(),
                reason=ResponseBs4XmlParser._get_text_or_cdata(
                    action_elem.find("reason")
                ),
                arguments=ResponseBs4XmlParser._parse_arguments(action_elem),
            )

            return Response(
                thought=Thought(
                    reasoning=ResponseBs4XmlParser._get_text_or_cdata(
                        thought_elem.find("reasoning")
                    ),
                    to_do=to_do_steps,
                    done=done_steps,
                ),
                action=action,
            )

        except Exception as e:
            raise ValueError(f"Error parsing XML data: {str(e)}") from e


# Example usage
if __name__ == "__main__":
    xml_example = """
    <response>
        <thought>
            <reasoning>Based on the analysis, the steps required are clear.</reasoning>
            <to_do>
                <step>
                    <name>gather_data</name>
                    <description>Collect relevant data from the database.</description>
                    <reason>Data is necessary for the analysis.</reason>
                    <result>Data gathered successfully.</result>
                    <depends_on_steps>
                        <step_name>initialize</step_name>
                    </depends_on_steps>
                </step>
            </to_do>
            <done>
                <step>
                    <name>initialize</name>
                    <description>Initialize the database connection.</description>
                    <reason>Connection required to gather data.</reason>
                    <result>Database connection established.</result>
                    <depends_on_steps/>
                </step>
            </done>
        </thought>
        <action>
            <tool_name>data_collector</tool_name>
            <reason>Selected for its efficiency in gathering large data sets.</reason>
            <arguments>
                <argument1><![CDATA[main_db]]></argument1>
                <argument2><![CDATA[100]]></argument2>
            </arguments>
        </action>
    </response>
    """

    try:
        response_obj = ResponseBs4XmlParser.parse(xml_example)
        print(response_obj.model_dump_json(indent=2))
    except ValueError as e:
        print(f"Error: {e}")
