import datetime
import json
import os
import sqlite3 as sqlite
from sqlite3 import Connection, Row
from typing import Optional, Union

import attr


def _from_dict(cls, obj):
    if obj is None:
        return None
    elif isinstance(obj, cls):
        return obj
    else:
        return cls(**json.loads(obj))


def _convert_date(date: Union[datetime.date, str]) -> Optional[datetime.date]:
    if date is None:
        return None
    elif isinstance(date, datetime.date):
        return date
    else:
        return datetime.date.fromtimestamp(float(date))


@attr.s(auto_attribs=True)
class Book(object):
    id: int
    title: str
    first_published: int
    edition: int
    added: datetime.date = attr.ib(converter=_convert_date)
    notes: str

    @property
    def authors(self) -> list["BookAuthor"]:
        return self._authors

    @authors.setter
    def authors(self, value: list["BookAuthor"]) -> None:
        self._authors = value
        self.has_dirty_relations = True

    @property
    def genres(self) -> list["BookGenre"]:
        return self._genres

    @genres.setter
    def genres(self, value: list["BookGenre"]) -> None:
        self._genres = value
        self.has_dirty_relations = True

    @property
    def readings(self) -> list["BookReader"]:
        return self._readings

    @readings.setter
    def readings(self, value: list["BookReader"]) -> None:
        self._readings = value
        self.has_dirty_relations = True

    @property
    def wishlists(self) -> list["Wishlist"]:
        return self._wishlists

    @wishlists.setter
    def wishlists(self, value: list["Wishlist"]) -> None:
        self._wishlists = value
        self.has_dirty_relations = True

    @property
    def has_dirty_relations(self) -> bool:
        return self._has_dirty_relations

    @has_dirty_relations.setter
    def has_dirty_relations(self, value: bool) -> None:
        self._has_dirty_relations = value


def book_from_dict(obj: Union[str, Book]) -> Book:
    return _from_dict(Book, obj)


@attr.s(auto_attribs=True)
class Author(object):
    id: int
    name: str


def author_from_dict(obj: Union[str, Author]) -> Author:
    return _from_dict(Author, obj)


@attr.s(auto_attribs=True)
class Genre(object):
    id: int
    name: str


def genre_from_dict(obj: Union[str, Genre]) -> Genre:
    return _from_dict(Genre, obj)


@attr.s(auto_attribs=True)
class Reader(object):
    id: int
    name: str


def reader_from_dict(obj: Union[str, Reader]) -> Reader:
    return _from_dict(Reader, obj)


@attr.s(auto_attribs=True)
class Publisher(object):
    id: int
    name: str


def publisher_from_dict(obj: Union[str, Publisher]) -> Publisher:
    return _from_dict(Publisher, obj)


@attr.s(auto_attribs=True)
class BookGenre(object):
    id: int
    book: Book = attr.ib(converter=book_from_dict)
    genre: Genre = attr.ib(converter=genre_from_dict)


@attr.s(auto_attribs=True)
class BookAuthor(object):
    id: int
    book: Book = attr.ib(converter=book_from_dict)
    author: Author = attr.ib(converter=author_from_dict)


@attr.s(auto_attribs=True)
class BookReader(object):
    id: int
    reader: Reader = attr.ib(converter=reader_from_dict)
    book: Book = attr.ib(converter=book_from_dict)
    start: datetime.date = attr.ib(converter=_convert_date)
    end: datetime.date = attr.ib(converter=_convert_date)
    dropped: bool
    notes: str


@attr.s(auto_attribs=True)
class Wishlist(object):
    id: int
    reader: Reader = attr.ib(converter=reader_from_dict)
    book: Book = attr.ib(converter=book_from_dict)


def create_db(fn: str) -> Connection:
    db = sqlite.connect(fn)
    db.row_factory = sqlite.Row

    if (
        db.execute("SELECT name from sqlite_schema where name = 'Books'").fetchone()
        is None
    ):
        init_db(db)

    return db


def init_db(db: Connection):
    classes = [
        Book,
        Author,
        Genre,
        Reader,
        Publisher,
        BookGenre,
        BookAuthor,
        BookReader,
        Wishlist,
    ]

    def _def_col(att: attr.Attribute) -> str:
        if att.name == "id":
            return "id INTEGER PRIMARY KEY AUTOINCREMENT"
        elif att.type in classes:
            return f"{att.name} REFERENCES {att.type.__name__}s (id)"
        else:
            return f"{att.name}"

    with db:
        for c in classes:
            cols = " , ".join(_def_col(att) for att in attr.fields(c))
            db.execute(f"CREATE TABLE {c.__name__}s({cols})")


def make_test_db(fn: str = ":memory:") -> Connection:
    try:
        os.remove(fn)
    except:
        pass

    db = create_db(fn)

    with db:
        db.executescript(
            """
            pragma foreign_keys = on;

            insert into Readers(name)
            values ('Fran'), ('Maria Ines');

            insert into Publishers(name)
            values ('Catedra');

            insert into Authors(name)
            values ('Euripides'), ('Juan Antonio Lopez Ferez');

            insert into Genres(name)
            values ('Classics'), ('Drama');

            insert into Books(title, first_published, edition)
            values ('Tragedias I', '-406', '11');

            insert into BookGenres(book, genre)
            values (1, 1), (1, 2);

            insert into BookAuthors(book, author)
            values (1, 1), (1, 2);

            insert into BookReaders(book, reader, start, end, dropped, notes)
            values (1, 1, strftime('%s', date('2021-01-05')), strftime('%s', date('2021-01-10')), False, Null);

            insert into Wishlists(reader, book)
            values (1, 1);

            """
        )

    return db


class Controller(object):
    def __init__(self, fn: str, user_id: int) -> None:
        self.db = make_test_db(fn)
        self.user = self.get_reader(user_id)

    def get_all_books(self) -> list[Row]:
        rows = self.db.execute(
            """
            select Books.id, title, Authors.authors, Genres.genres, first_published, notes
            from Books left join
                 (
                  select b.id, group_concat(a.name) as authors
                  from Books as b join BookAuthors as ba on b.id = ba.book
                                  join Authors as a on ba.author = a.id
                  group by b.id
                 ) as Authors on Books.id = Authors.id left join
                 (
                  select b.id, group_concat(g.name) as genres
                  from Books as b join BookGenres as bg on b.id = bg.book
                                  join Genres as g on bg.genre = g.id
                  group by b.id
                 ) as Genres on Books.id = Genres.id
            """
        ).fetchall()

        return rows

    def get_book(self, id: int):
        try:
            book_row = self.db.execute(
                "select * from Books where id = ?", [id]
            ).fetchone()
            author_rows = self.db.execute(
                """select BookAuthors.id as id,
                          json_object('id', Authors.id, 'name', name) as author
                from BookAuthors join Authors on BookAuthors.author = Authors.id
                where BookAuthors.book = ?""",
                [id],
            ).fetchall()
            genre_rows = self.db.execute(
                """select BookGenres.id as id,
                          json_object('id', Genres.id, 'name', name) as genre
                from BookGenres join Genres on BookGenres.genre = Genres.id
                where BookGenres.book = ?""",
                [id],
            ).fetchall()
            reading_rows = self.db.execute(
                """select BookReaders.id as id,
                          json_object('id', Readers.id, 'name', name) as reader,
                          start, end, dropped, notes
                from BookReaders join Readers on BookReaders.reader = Readers.id
                where BookReaders.book = ?""",
                [id],
            ).fetchall()
            wishlist_rows = self.db.execute(
                """select Wishlists.id as id,
                          json_object('id', Readers.id, 'name', name) as reader
                from Wishlists join Readers on Wishlists.reader = Readers.id
                where Wishlists.book = ?""",
                [id],
            ).fetchall()
        except Exception as e:
            raise e
        book = Book(**book_row)
        book.authors = [BookAuthor(book=book, **row) for row in author_rows]
        book.genres = [BookGenre(book=book, **row) for row in genre_rows]
        book.readings = [BookReader(book=book, **row) for row in reading_rows]
        book.wishlists = [Wishlist(book=book, **row) for row in wishlist_rows]
        book.has_dirty_relations = False
        return book

    def get_reader(self, id: int) -> Reader:
        row = self.db.execute("select * from Readers where id = ?", [id]).fetchone()
        return Reader(**row)

    def get_or_make_book_author(self, book: Book, name: str) -> BookAuthor:
        row = self.db.execute("select * from Authors where name = ?", [id]).fetchone()
        if row is None:
            author = Author(-1, name)
        else:
            author = Author(**row)
        return BookAuthor(-1, book=book, author=author)

    def get_or_make_book_genre(self, book: Book, name: str) -> BookGenre:
        row = self.db.execute("select * from Genres where name = ?", [id]).fetchone()
        if row is None:
            genre = Genre(-1, name)
        else:
            genre = Genre(**row)
        return BookGenre(-1, book=book, genre=genre)
