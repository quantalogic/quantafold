from typing import Optional, List
from lxml import etree
from pydantic import ValidationError
from .response import Response, Step


class ResponseXmlParser:
    """Utility class to parse XML and create a Response object."""

    @staticmethod
    def _safe_find_text(element: etree._Element, path: str, default: str = "") -> str:
        """Safely find and return element text with a default value."""
        found = element.find(path) if element is not None else None
        return found.text if found is not None and found.text is not None else default

    @staticmethod
    def _parse_steps(parent_elem: etree._Element, step_container: str) -> List[dict]:
        """Parse steps from a container element safely."""
        steps = []
        if parent_elem is None:
            return steps

        container = parent_elem.find(step_container)
        if container is None:
            return steps

        for step in container.findall("step"):
            if step is not None:
                depends_on_elem = step.find("depends_on_steps")
                depends_on = []
                if depends_on_elem is not None:
                    depends_on = [
                        dep.text
                        for dep in depends_on_elem.findall("step_name")
                        if dep is not None and dep.text is not None
                    ]

                step_data = {
                    "name": ResponseXmlParser._safe_find_text(
                        step, "name", "unnamed_step"
                    ),
                    "description": ResponseXmlParser._safe_find_text(
                        step, "description", ""
                    ),
                    "reason": ResponseXmlParser._safe_find_text(step, "reason", ""),
                    "result": ResponseXmlParser._safe_find_text(step, "result"),
                    "depends_on_steps": depends_on,
                }
                steps.append(step_data)
        return steps

    @staticmethod
    def _parse_arguments(action_elem: etree._Element) -> dict:
        """Parse arguments safely."""
        arguments = {}
        if action_elem is None:
            return arguments

        args_elem = action_elem.find("arguments")
        if args_elem is None:
            return arguments

        for arg in args_elem.findall("arg"):
            if arg is not None:
                name = ResponseXmlParser._safe_find_text(arg, "name")
                value = ResponseXmlParser._safe_find_text(arg, "value")
                if name:
                    arguments[name] = value
        return arguments

    @staticmethod
    def parse(xml_data: str) -> Response:
        """Parse XML string to create a Response object."""
        try:
            root = etree.fromstring(xml_data)
            
            # Check which format we're dealing with
            if root.find("answer") is not None:
                # Format 2 - Simple response with thought and answer
                response_data = {
                    "thought": ResponseXmlParser._safe_find_text(root, "thought"),
                    "answer": ResponseXmlParser._safe_find_text(root, "answer"),
                }
            else:
                # Format 1 - Complex response with thought object and action
                thought_elem = root.find("thought")
                action_elem = root.find("action")
                
                response_data = {
                    "thought": {
                        "reasoning": ResponseXmlParser._safe_find_text(thought_elem, "reasoning"),
                        "to_do": ResponseXmlParser._parse_steps(thought_elem, "to_do"),
                        "done": ResponseXmlParser._parse_steps(thought_elem, "done"),
                    },
                    "action": {
                        "tool_name": ResponseXmlParser._safe_find_text(action_elem, "tool_name", "no_tool"),
                        "reason": ResponseXmlParser._safe_find_text(action_elem, "reason"),
                        "arguments": ResponseXmlParser._parse_arguments(action_elem),
                    },
                }

            return Response(**response_data)

        except etree.XMLSyntaxError as e:
            raise ValueError("Malformed XML data.") from e
        except ValidationError as e:
            raise ValueError("Validation error while creating Response object.") from e
        except Exception as e:
            raise ValueError(f"Unexpected error parsing XML: {str(e)}") from e


# Update the example usage section
if __name__ == "__main__":
    # Format 1 example
    xml_example_1 = """
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

    # Format 2 example
    xml_example_2 = """
    <response>
        <thought><![CDATA[Based on the available information, I can answer directly.]]></thought>
        <answer><![CDATA[Here is the final answer in Markdown format.]]></answer>
    </response>
    """

    try:
        # Test Format 1
        response_1 = ResponseXmlParser.parse(xml_example_1)
        print("Format 1 parsed successfully:")
        print(response_1.model_dump_json(indent=2))

        # Test Format 2
        response_2 = ResponseXmlParser.parse(xml_example_2)
        print("\nFormat 2 parsed successfully:")
        print(response_2.model_dump_json(indent=2))
    except ValueError as e:
        print(f"Error: {e}")
