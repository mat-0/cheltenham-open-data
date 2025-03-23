 # importing modules
import helper
import feedparser
import pathlib

root = pathlib.Path(__file__).parent.parent.resolve()
url = root / "_data/fix-my-street.xml"
string_output = ""
entries = feedparser.parse(url)["entries"]
for entry in entries:
    string_output += f"\n- {entry['title']} :- [{entry['link']}]({entry['link']})"

if __name__ == "__main__":
    readme = root / "_pages/fix-my-street.md"
    readme_contents = readme.open().read()
    final_output = helper.replace_chunk(readme_contents,"fix_marker",f'{string_output}\n')
    readme.open("w").write(final_output)
    print("Fix My Street data updated successfully")

