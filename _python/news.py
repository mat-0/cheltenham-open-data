# importing modules
import pathlib
import feedparser
import yaml
import helper
from datetime import datetime, timedelta


def clean_title(title):
    """Strip pipe characters that break markdown tables."""
    return title.replace("|", "").strip()


def load_sources(config_path):
    with config_path.open() as f:
        config = yaml.safe_load(f)
    return config["sources"]


# processing
if __name__ == "__main__":
    try:
        root = pathlib.Path(__file__).parent.parent.resolve()
        config_path = root / "_data/news-sources.yml"

        sources = load_sources(config_path)
        all_items = []

        for source in sources:
            feed = feedparser.parse(source["url"])
            for item in feed["items"][:25]:
                if not item.get("title", "").strip():
                    continue
                item["source_title"] = source["title"]
                all_items.append(item)

        all_items.sort(key=lambda x: x["published_parsed"], reverse=True)

        cutoff_date = datetime.now() - timedelta(days=30)
        all_items = [
            item for item in all_items
            if datetime(*item["published_parsed"][:6]) > cutoff_date
        ]

        string = ""
        for item in all_items:
            title = clean_title(item["title"])
            date_str = datetime(*item["published_parsed"][:6]).strftime("%d %b %Y")
            string += f"- {title} - From [{item['source_title']}]({item['link']}) on {date_str}\n"

        f = root / "_pages/news.md"
        m = f.open().read()
        c = helper.replace_chunk(m, "news_marker", string)
        f.open("w").write(c)
        print("News completed")

    except FileNotFoundError:
        print("File does not exist, unable to proceed")
    except KeyError as e:
        print(f"Missing expected key in news-sources.yml: {e}")