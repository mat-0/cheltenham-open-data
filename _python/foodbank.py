# import
from requests import get
import json
import pathlib
import os

city = os.getenv('city_code') or 'cheltenham'

def get_data_from_endpoint():
    endpoint = (f'https://www.givefood.org.uk/api/2/foodbank/Cheltenham/')
    response = get(endpoint, timeout=10)
    if response.status_code >= 400:
        raise RuntimeError(f'Request failed: { response.text }')
    return response.json()

# output
if __name__ == "__main__":
    root = pathlib.Path(__file__).parent.parent.resolve()
    with open( root / "_data/foodbank.json", 'r+') as filehandler:
        data = json.load(filehandler)
        new_data = get_data_from_endpoint()
        filehandler.seek(0)
        json.dump(new_data, filehandler, indent=4)