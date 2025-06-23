import requests
from bs4 import BeautifulSoup
from narratives.utils.date_time_helpers import normalize_to_utc
from narratives.utils.random_sleep import random_sleep
from datetime import datetime
import pytz


EXTERNAL_GENRE_MAPPING = {
    "Briefings & Statements": "speech",
    "Press Releases": "press_release",
    "Remarks": "speech",
    "Fact Sheets": "fact_sheet",
}

class WhiteHouseTranslator:

    def parse(self, raw_html, source_timezone="UTC"):
        soup = BeautifulSoup(raw_html, "html.parser")
        title_blocks = soup.find_all("h2", class_="wp-block-post-title")
        rawtexts = []

        for title_tag in title_blocks:
            link_tag = title_tag.find("a")
            if not link_tag:
                continue

            title = link_tag.get_text().strip()
            full_url = link_tag["href"]

            # Genre extraction
            internal_genre = "other"
            genre_block = title_tag.find_parent().find("div", class_="taxonomy-category wp-block-post-terms")
            if genre_block:
                genre_link = genre_block.find("a")
                if genre_link:
                    external_genre = genre_link.get_text().strip()
                    internal_genre = EXTERNAL_GENRE_MAPPING.get(external_genre, "other")

            # Published date extraction with timezone conversion
            published_at = None
            parent_container = title_tag.find_parent()
            date_block = parent_container.find("div", class_="wp-block-post-date")
            if date_block:
                time_tag = date_block.find("time")
                if time_tag and time_tag.has_attr("datetime"):
                    raw_dt = time_tag["datetime"]
                    try:
                        published_at = normalize_to_utc(raw_dt, source_timezone)
                    except Exception as e:
                        print(f"Failed parsing datetime: {e}")

            # Fetch full article content with random sleep
            random_sleep(4, 12)
            content_html = requests.get(full_url).text
            content_soup = BeautifulSoup(content_html, "html.parser")

            paragraphs = [
                p.get_text().strip()
                for p in content_soup.find_all("p")
                if p.get_text().strip()
            ]
            full_content = "\n\n".join(paragraphs)

            rawtexts.append({
                "title": title,
                "subtitle": None,
                "author": None,
                "content": full_content,
                "content_paragraphs": paragraphs,
                "published_at": published_at,
                "source": None,
                "genre": internal_genre,
                "source_url": full_url  # ✅ Full original URL stored
            })

        return rawtexts
