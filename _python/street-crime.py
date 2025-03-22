
import json
import pathlib
import os
import re
from requests import get
import helper


if __name__ == "__main__":
    root = pathlib.Path(__file__).parent.parent.resolve()

    with open( root / "_data/AA3_stops_street.json", 'r+') as filehandler:
        data = json.load(filehandler)
        new_data = helper.et_data("https://data.police.uk/api/crimes-street/stops-street?lat=51.9042&lng=-2.10141")
        filehandler.seek(0)
        json.dump(new_data, filehandler, indent=4)

    with open( root / "_data/AA3_all_crime.json", 'r+') as filehandler:
        data = json.load(filehandler)
        new_data = helper.get_data("https://data.police.uk/api/crimes-street/all-crime?lat=51.9042&lng=-2.10141")
        filehandler.seek(0)
        json.dump(new_data, filehandler, indent=4)


    rows = ""
    # output
    if __name__ == "__main__":
        root = pathlib.Path(__file__).parent.parent.resolve()
        with open( root / "_data/AA3_all_crime.json", 'r+') as filehandler:
            crimes = json.load(filehandler)
            for crime in crimes:
                rows += f"\n<tr><td>{crime['id']}</td><td>{crime['category']}</td><td>{crime['month']}</td><td>{crime['location']['street']['name']}</td></tr>"
    index_page = root / "index.html"
    index_contents = index_page.open().read()
    final_output = helper.replace_chunk(index_contents, "table_marker", f"{rows}")
    index_page.open("w").write(final_output)