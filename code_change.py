import os
import re
import sys
import xml.etree.ElementTree as ET


def extract_code_changes_from_markdown(markdown_file):
    """Extract <code_changes> content from a markdown file."""
    with open(markdown_file, "r", encoding="utf-8") as file:
        content = file.read()

    # Extract <code_changes> block using regex
    match = re.search(r"(<code_changes>.*?</code_changes>)", content, re.DOTALL)

    if not match:
        raise ValueError("No <code_changes> found in the markdown file.")

    return match.group(1)





def validate_file_block(file_block):
    """Validate the presence of required tags in a file block."""
    required_tags = {
        "file_summary": "<file_summary>(.*?)</file_summary>",
        "file_operation": "<file_operation>(.*?)</file_operation>",
        "file_path": "<file_path>(.*?)</file_path>",
    }

    results = {}
    for tag, regex in required_tags.items():
        match = re.search(regex, file_block, re.DOTALL)
        if match:
            results[tag] = match.group(1)  # Extract matched content
        else:
            raise ValueError(f"Missing required tag: <{tag}> in <file> block.")

    # Check if <file_code> is present if operation is not DELETE:
    if results["file_operation"] != "DELETE":
        file_code_match = re.search(
            r"<file_code>(.*?)</file_code>", file_block, re.DOTALL
        )
        if not file_code_match:
            raise ValueError("Missing required tag: <file_code> in <file> block.")

        # Parse the <file_code> as XML
        try:
            # Remove CDATA and parse as XML
            xml_content = file_code_match.group(1)
            root = ET.fromstring(f"<root>{xml_content}</root>")
            results["file_code"] = root.text
        except ET.ParseError:
            raise ValueError("Invalid XML format in <file_code>.")

    return results


def apply_code_changes(code_changes):
    """Apply the changes specified in the code changes section."""

    # Extract all <file> blocks
    files = re.findall(r"<file>(.*?)</file>", code_changes, re.DOTALL)

    for file_block in files:
        try:
            file_data = validate_file_block(file_block)

            # Perform the specified file operation
            file_operation = file_data["file_operation"]
            file_path = file_data["file_path"]
            file_code = file_data.get("file_code", "")  # Default to empty for DELETE operations

            if file_operation in ["UPDATE", "CREATE"]:
                print(f"Creating/updating file: {file_path}")
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_code.strip())  # Write the code with proper formatting
            elif file_operation == "DELETE":
                print(f"Deleting file: {file_path}")
                if os.path.isfile(file_path):
                    os.remove(file_path)
            else:
                print(f"Unknown file operation: {file_operation}")
            print(f"Processed: {file_data['file_summary']}")

        except ValueError as e:
            print(f"Error in file block: {e}")

    print("Code changes applied successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python apply_code_changes.py <input_markdown_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    try:
        code_changes_xml = extract_code_changes_from_markdown(input_file)
        apply_code_changes(code_changes_xml)
    except ValueError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)