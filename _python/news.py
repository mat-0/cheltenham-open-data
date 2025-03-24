# importing modules
import pathlib
import feedparser
import helper
from datetime import datetime, timedelta

URL_1 ="http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/england/gloucestershire/rss.xml"
URL_2 ="https://www.gloucestershire.police.uk/news/gloucestershire/news/GetNewsRss/"
URL_3 ="https://gloucesternewscentre.co.uk/category/gloucestershire-news/cheltenham-news/feed/"
URL_4 ="https://www.cheltenham.gov.uk/rss/news"


def time_ago(published_parsed):
            published_date = datetime(*published_parsed[:6])
            now = datetime.now()
            diff = now - published_date
            if diff.days > 0:
                return f"{diff.days} days ago"
            elif diff.seconds > 3600:
                return f"{diff.seconds // 3600} hours ago"
            elif diff.seconds > 60:
                return f"{diff.seconds // 60} minutes ago"
            else:
                return "just now"



# processing
if __name__ == "__main__":
    try:
        root = pathlib.Path(__file__).parent.parent.resolve()

        urls = [URL_1, URL_2, URL_3, URL_4]
        all_items = []

        for URL in urls:
            feed = feedparser.parse(URL)
            all_items.extend(feed["items"][:25])

        all_items.sort(key=lambda x: x["published_parsed"], reverse=True)


        for item in all_items:
            item["published"] = time_ago(item["published_parsed"])

            cutoff_date = datetime.now() - timedelta(days=30)
            all_items = [item for item in all_items if datetime(*item["published_parsed"][:6]) > cutoff_date]

        string = ""
        for item in all_items:
            string += f"- {item['title']} ({item['published']})\n"

        f = root / "_pages/news.md"
        m = f.open().read()
        c = helper.replace_chunk(m, "news_marker", string)
        f.open("w").write(c)
        print("News completed")

    except FileNotFoundError:
        print("File does not exist, unable to proceed")