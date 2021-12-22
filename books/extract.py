import datetime
import locale
import re
from typing import Iterator

from books import model
import requests
from bs4 import BeautifulSoup
from requests.compat import urljoin


OLURL = "https://openlibrary.org/"


def import_book(url: str, controller: model.Controller) -> model.Book:
    text = requests.get(url).text
    bs = BeautifulSoup(text, "lxml")
    isbn = bs.find(itemprop="isbn").text

    try:
        book = controller.get_book_isbn(isbn)
    except Exception:
        pass
    else:
        raise ValueError(
            f"Book at {url} with isbn {isbn} already exists in the database"
        )

    book_info_dict = requests.get(urljoin(OLURL, f"/isbn/{isbn}.json")).json()

    if (match := re.search(r"\d\d\d\d", book_info_dict["publish_date"])) is None:
        pub_year = 0
    else:
        pub_year = match.group()

    book = model.Book(
        None, book_info_dict["title"], pub_year, 0, datetime.date.today(), "", isbn
    )

    authors_dict = list(get_authors_dict(book_info_dict["authors"]))
    book.authors = [
        controller.get_or_make_book_author(book, author["name"])
        for author in authors_dict
    ]

    genres_list = [tag.text for tag in bs.find_all("a", class_="bookPageGenreLink")]
    book.genres = [
        controller.get_or_make_book_genre(book, genre) for genre in genres_list
    ]

    book.publishers = [
        controller.get_or_make_book_publisher(book, publisher)
        for publisher in book_info_dict["publishers"]
    ]

    return book


def get_authors_dict(authors: dict) -> Iterator[dict]:
    for author in authors:
        author_key = author["key"]
        author_dict = requests.get(urljoin(OLURL, f"{author_key}.json")).json()
        yield author_dict
