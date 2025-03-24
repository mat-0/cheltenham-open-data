# importing modules
import pathlib
import feedparser
import helper

URL_1 ="https://www.gloucestershirelive.co.uk/?service=rss"
URL_2 ="http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/england/gloucestershire/rss.xml"



# processing
if __name__ == "__main__":
    try:
        root = pathlib.Path(__file__).parent.parent.resolve()

        urls = [URL_1, URL_2]
        all_items = []

        for URL in urls:
            feed = feedparser.parse(URL)
            all_items.extend(feed["items"][:25])

        all_items.sort(key=lambda x: x["published_parsed"], reverse=True)

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