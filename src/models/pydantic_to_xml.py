from typing import Any, List, Optional

from lxml import etree
from pydantic import BaseModel


class PydanticToXMLSerializer:
    @staticmethod
    def serialize(
        obj: BaseModel,
        pretty: bool = False,
        lowercase: bool = False,
        include_declaration: bool = False,
        cdata_fields: Optional[List[str]] = None,
        auto_cdata: bool = False,  # New parameter for automatic CDATA wrapping
    ) -> str:
        """Serialize a Pydantic model to an XML string with optional CDATA support."""
        root_name = (
            obj.__class__.__name__.lower() if lowercase else obj.__class__.__name__
        )
        root = etree.Element(root_name)

        def needs_cdata(value: Any) -> bool:
            """Check if the value needs CDATA wrapping."""
            if isinstance(value, str):
                return any(char in value for char in ["<", ">", "&"])
            return False

        def build_xml(element: etree.Element, obj_dict: Any) -> None:
            """Recursive helper to build the XML structure."""
            if isinstance(obj_dict, BaseModel):
                obj_dict = obj_dict.model_dump(by_alias=True)

            if isinstance(obj_dict, dict):
                for key, value in obj_dict.items():
                    element_key = key.lower() if lowercase else key
                    sub_element = etree.SubElement(element, element_key)

                    if isinstance(value, BaseModel):
                        # If it's a nested Pydantic model, recurse
                        build_xml(sub_element, value)
                    elif isinstance(value, dict):
                        # If it's a nested dictionary, recurse
                        build_xml(sub_element, value)
                    elif isinstance(value, list):
                        # Handle lists of items
                        for item in value:
                            item_element = etree.SubElement(sub_element, "item")
                            if isinstance(item, (BaseModel, dict)):
                                # If the item is a nested Pydantic model or dictionary
                                build_xml(item_element, item)
                            else:
                                # Handle primitive types or other non-model items
                                if (cdata_fields and key in cdata_fields) or (
                                    auto_cdata and needs_cdata(item)
                                ):
                                    item_element.text = etree.CDATA(str(item))
                                else:
                                    item_element.text = str(item)
                    else:
                        # Handling CDATA wrapping based on both cdata_fields and auto_cdata
                        if (cdata_fields and key in cdata_fields) or (
                            auto_cdata and needs_cdata(value)
                        ):
                            sub_element.text = etree.CDATA(str(value))
                        else:
                            sub_element.text = str(value)
            elif isinstance(obj_dict, list):
                for item in obj_dict:
                    item_element = etree.SubElement(element, "item")
                    if isinstance(item, (BaseModel, dict)):
                        build_xml(item_element, item)
                    else:
                        if auto_cdata and needs_cdata(item):
                            item_element.text = etree.CDATA(str(item))
                        else:
                            item_element.text = str(item)
            else:
                # For primitive types
                if auto_cdata and needs_cdata(obj_dict):
                    element.text = etree.CDATA(str(obj_dict))
                else:
                    element.text = str(obj_dict)

        # Build the XML structure
        build_xml(root, obj)

        # Convert the XML structure to a string
        xml_string = etree.tostring(root, encoding="unicode", pretty_print=pretty)

        if include_declaration:
            # Include XML declaration at the top
            xml_string = f'<?xml version="1.0" ?>\n{xml_string}'

        return xml_string


# Example Usage
class Address(BaseModel):
    street: str
    city: str
    zip_code: str


class User(BaseModel):
    id: int
    name: str
    email: str
    tags: List[str]
    address: Address  # Nested Pydantic model


def main():
    # Create a Pydantic model instance with nested structures and lists
    user = User(
        id=1,
        name="John & Doe <Example>",
        email="johndoe@example.com",
        tags=["developer", "python", "pydantic"],
        address=Address(street="123 Main St", city="Anytown", zip_code="12345"),
    )

    # Specify which fields should be wrapped in CDATA
    cdata_fields = ["email"]  # Only email is explicitly specified for CDATA

    # Serialize to XML with lowercase class names, include XML declaration,
    # and activate auto CDATA wrapping
    xml_string = PydanticToXMLSerializer.serialize(
        user,
        pretty=True,
        lowercase=True,
        include_declaration=True,
        cdata_fields=cdata_fields,
        auto_cdata=True,  # Activate automatic CDATA wrapping
    )

    print(xml_string)


if __name__ == "__main__":
    main()
