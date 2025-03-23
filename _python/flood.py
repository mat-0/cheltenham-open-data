import helper
import json
import pathlib
import xml.etree.ElementTree as ET

if __name__ == "__main__":
        data = helper.fetch_flood_data()
        with open("_data/flood.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Data saved to feed.json")

        with open("_data/flood.json", "r") as f:
            data = json.load(f)
        helper.convert_to_rss(data, "flood.xml")

        print("RSS feed saved to flood.xml")

        tree = ET.parse('flood.xml')
        root = tree.getroot()

        output = ""

        for item in root.findall('./channel/item'):
            title = item.find('title').text
            description = item.find('description').text
            output += f"- {title}\n"
            output += f"- {description}\n"

        root = pathlib.Path(__file__).parent.parent.resolve()

        md = root / "_pages/flood-warnings.md"
        md_contents = md.open().read()
        md_contents = helper.replace_chunk(md_contents,"flood_marker", output)
        md.open("w").write(md_contents)