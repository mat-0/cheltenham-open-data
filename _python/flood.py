
import helper
import json

if __name__ == "__main__":
        data = helper.fetch_flood_data()
        with open("feed.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Data saved to feed.json")

        with open("feed.json", "r") as f:
            data = json.load(f)
        helper.convert_to_rss(data, "feed.xml")

        print("RSS feed saved to feed.xml")
