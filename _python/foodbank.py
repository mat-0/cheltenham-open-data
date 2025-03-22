# importing modules
import helper
import pathlib
import json
from requests import get
import os


if __name__ == "__main__":
    root = pathlib.Path(__file__).parent.parent.resolve()
    with open(root / "_data/foodbank.json", 'r') as filehandler:
        data = json.load(filehandler)
        needs = data['need']['needs']
        date = helper.date_to_iso(data['need']['created'])
        output = f"## List of needed items in Cheltenham\n\n"
        output += f"Last updated: {date}\n\n"
        output += f"- {needs}".replace("\n", "\n- ")
        output.rstrip("-")
        address = data['address'].replace("\r\n"," ")
        contact_string = (f"- Email: {data['email']}\n"
                        f"- Tel: {data['phone']}\n"
                        f"- Address: {address}\n"
                        f"- Network: {data['network']}\n"
                        f"- Charity number: [{data['charity']['registration_id']}]({data['charity']['register_url']})")

    md = root / "_pages/food-bank.md"
    md_contents = md.open().read()
    md_contents = helper.replace_chunk(md_contents,"summary_marker",output)
    md_contents = helper.replace_chunk(md_contents,"contact_marker",contact_string)
    md.open("w").write(md_contents)

