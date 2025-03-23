import json
import pathlib
import helper


if __name__ == "__main__":
    root = pathlib.Path(__file__).parent.parent.resolve()
    rows = ""
    # output
    if __name__ == "__main__":
        root = pathlib.Path(__file__).parent.parent.resolve()
        with open( root / "_data/AA3_all_crime.json", 'r+') as filehandler:
            crimes = json.load(filehandler)
            for crime in crimes:
                rows += f"\n<tr><td>{crime['id']}</td><td>{crime['category']}</td><td>{crime['month']}</td><td>{crime['location']['street']['name']}</td></tr>"
    md_page = root / "_pages/street-crime.md"
    md_contents = md_page.open().read()
    final_output = helper.replace_chunk(md_contents, "table_marker", f"{rows}")
    md_page.open("w").write(final_output)
    print("Crime Data updated")
