import datetime
import locale
import re
from typing import Iterator
import logging

from qtbooks import model
import requests
from bs4 import BeautifulSoup
from requests.compat import urljoin

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
}


def import_book(url: str, controller: model.Controller) -> model.Book:
    max_attempts = 3
    for i in range(max_attempts):
        try:
            text = requests.get(url, headers=HEADERS).text
            bs = BeautifulSoup(text, "lxml")
            isbn = bs.find(property="books:isbn")["content"]
            break
        except Exception as e:
            logger.warning(
                f"Failed to obtain goodreads page, attempt {i+1}/{max_attempts}"
            )
            if i == max_attempts - 1:
                raise ConnectionError(f"URL {url} did not yield an ISBN")

    title = bs.find(id="bookTitle", itemprop="name").text.lstrip().rstrip()
    pub_tag = bs.find(text=re.compile("Published"))
    if pub_tag is not None and (match := re.search(r"-?\d\d\d\d", pub_tag)) is not None:
        pub_year = int(match.group())
    else:
        pub_year = 0

    if pub_tag is not None and (match := re.search(r"by (.*)\n", pub_tag)) is not None:
        publisher = match.group(1)
    else:
        publisher = None

    first_pub_tag = bs.find(text=re.compile("first published"))
    if (
        first_pub_tag is not None
        and (match := re.search(r"-?\d\d\d\d", first_pub_tag)) is not None
    ):
        pub_year = int(match.group())

    authors = [tag.text for tag in bs.find(id="bookAuthors").find_all(itemprop="name")]
    genres_list = list(
        dict.fromkeys(
            [tag.text for tag in bs.find_all("a", class_="bookPageGenreLink")]
        )
    )

    already_exists = False
    if isbn is None:
        books = controller.get_books_title(title)
        auth_set = set(authors)
        for book in books:
            if auth_set == {auth.author.name for auth in book.authors}:
                already_exists = True
    else:
        try:
            book = controller.get_book_isbn(isbn)
        except Exception:
            pass
        else:
            already_exists = True

    if already_exists:
        raise ValueError(f"Book at {url} already exists in the database")

    book = model.Book(None, title, pub_year, 0, datetime.date.today(), "", isbn)
    book.authors = [
        controller.get_or_make_book_author(book, author) for author in authors
    ]
    book.genres = [
        controller.get_or_make_book_genre(book, genre) for genre in genres_list
    ]
    # FIXME multiple publishers?
    if publisher is not None:
        book.publishers = [controller.get_or_make_book_publisher(book, publisher)]

    return book
