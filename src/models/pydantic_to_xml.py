from typing import Any, Dict, List, Optional

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
    ) -> str:
        """Serialize a Pydantic model to an XML string with optional CDATA support."""
        root_name = (
            obj.__class__.__name__.lower() if lowercase else obj.__class__.__name__
        )
        root = etree.Element(root_name)

        obj_dict = obj.model_dump(by_alias=True)

        def build_xml(element: etree.Element, obj_dict: Dict[str, Any]) -> None:
            """Recursive helper to build the XML structure."""
            for key, value in obj_dict.items():
                element_key = key.lower() if lowercase else key
                sub_element = etree.SubElement(element, element_key)

                if isinstance(value, BaseModel):
                    build_xml(sub_element, value.model_dump(by_alias=True))
                elif isinstance(value, list):
                    for item in value:
                        item_element = etree.SubElement(sub_element, "item")
                        if isinstance(item, BaseModel):
                            build_xml(item_element, item.model_dump(by_alias=True))
                        else:
                            item_element.text = str(item)
                else:
                    # Handling CDATA wrapping
                    if cdata_fields and key in cdata_fields:
                        sub_element.text = etree.CDATA(str(value))
                    else:
                        sub_element.text = str(value)

        # Build the XML structure
        build_xml(root, obj_dict)

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
    # Create a Pydantic model instance
    user = User(
        id=1,
        name="John Doe",
        email="johndoe@example.com",
        tags=["developer", "python", "pydantic"],
        address=Address(street="123 Main St", city="Anytown", zip_code="12345"),
    )

    # Specify which fields should be wrapped in CDATA
    cdata_fields = ["name", "email"]

    # Serialize to XML with lowercase class names, include XML declaration, and CDATA wrapping
    xml_string = PydanticToXMLSerializer.serialize(
        user,
        pretty=True,
        lowercase=True,
        include_declaration=True,
        cdata_fields=cdata_fields,
    )
    print(xml_string)


if __name__ == "__main__":
    main()
