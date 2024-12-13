from lxml import etree
from pydantic import ValidationError

from .response import Response


class ResponseXmlParser:
    """Utility class to parse XML and create a Response object."""

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
            # Parse the XML data using lxml
            root = etree.fromstring(xml_data)

            # Extract thought details
            thought_elem = root.find("thought")
            reasoning = thought_elem.find("reasoning").text

            # Extract to_do steps
            to_do_steps = []
            for step in thought_elem.find("to_do").findall("step"):
                to_do_step = {
                    "name": step.find("name").text,
                    "description": step.find("description").text,
                    "reason": step.find("reason").text,
                    "result": step.find("result").text
                    if step.find("result") is not None
                    else None,
                    "depends_on_steps": [
                        dep.text
                        for dep in step.find("depends_on_steps").findall("step_name")
                    ],
                }
                to_do_steps.append(to_do_step)

            # Extract done steps
            done_steps = []
            for step in thought_elem.find("done").findall("step"):
                done_step = {
                    "name": step.find("name").text,
                    "description": step.find("description").text,
                    "reason": step.find("reason").text,
                    "result": step.find("result").text
                    if step.find("result") is not None
                    else None,
                    "depends_on_steps": [
                        dep.text
                        for dep in step.find("depends_on_steps").findall("step_name")
                    ],
                }
                done_steps.append(done_step)

            # Extract action details
            action_elem = root.find("action")
            tool_name = action_elem.find("tool_name").text
            reason = action_elem.find("reason").text

            arguments = {}
            for arg in action_elem.find("arguments").findall("arg"):
                arguments[arg.find("name").text] = arg.find("value").text

            # Create Response object
            response_data = {
                "thought": {
                    "reasoning": reasoning,
                    "to_do": to_do_steps,
                    "done": done_steps,
                },
                "action": {
                    "tool_name": tool_name,
                    "reason": reason,
                    "arguments": arguments,
                },
            }

            # Return a validated Response object
            return Response(**response_data)

        except etree.XMLSyntaxError as e:
            raise ValueError("Malformed XML data.") from e
        except ValidationError as e:
            raise ValueError("Validation error while creating Response object.") from e


# Example usage of ResponseXmlParser
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
    </response>
    """

    try:
        response_obj = ResponseXmlParser.parse(xml_example)
        print(response_obj.model_dump_json(indent=2))
    except ValueError as e:
        print(f"Error: {e}")
