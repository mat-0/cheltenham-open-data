# importing modules
import pathlib

import feedparser
import helper
from datetime import datetime

URL = "https://www.mi5.gov.uk/UKThreatLevel/UKThreatLevel.xml"

# processing
if __name__ == "__main__":
    try:
        root = pathlib.Path(__file__).parent.parent.resolve()
        output = feedparser.parse(URL)["entries"]

        for entry in output:
            level = (f"{entry['title']}")
            update = entry['published']
            update = datetime.strptime(
                update, "%A, %B %d, %Y -  %H:%M").strftime("%Y-%m-%d")
            days_since_update = (datetime.now() -
                                 datetime.strptime(update, "%Y-%m-%d")).days
            desc = entry['summary']

            level_class = level.split()[-1]


        string =  f'<h3>{level_class}</h3>\n'
        string += f'<div class="{level_class}">\n'
        string += f'<ul>\n'
        string += f'<li>{level}</li>\n'
        string += f'<li>It has been {days_since_update} days since the last change ({update})</li>\n'
        string += f'<li>Details: {desc}</li>\n'
        string += f'</ul>\n'
        string += f'</div>'
        f = root / "_pages/terrorism.md"
        m = f.open().read()
        c = helper.replace_chunk(m, "threat_marker", string)
        f.open("w").write(c)
        print("threat completed")

    except FileNotFoundError:
        print("File does not exist, unable to proceed")