
import helper
import json

if __name__ == "__main__":
        data = helper.fetch_flood_data()
        with open("_data/flood.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Data saved to feed.json")

        with open("_data/flood.json", "r") as f:
            data = json.load(f)
        helper.convert_to_rss(data, "flood.xml")

        print("RSS feed saved to flood.xml")
