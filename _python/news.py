# importing modules
import pathlib
import feedparser
import helper

# processing
if __name__ == "__main__":
    try:
        root = pathlib.Path(__file__).parent.parent.resolve()
        URL ="https://www.gloucestershirelive.co.uk/?service=rss"
        feed = feedparser.parse(URL)
        items = feed["items"][:20]
        string = "\n".join([f"* {item['title']})" for item in items])
        f = root / "_pages/news.md"
        m = f.open().read()
        c = helper.replace_chunk(m, "news_marker", string)
        f.open("w").write(c)
        print("News completed")

    except FileNotFoundError:
        print("File does not exist, unable to proceed")