import json
import re
import datetime
import os
import sqlite3 as sqlite
from functools import lru_cache
from sqlite3 import Connection, Row
from typing import Optional, Union, Iterator, List, Tuple, Dict
from pathlib import Path

from PyQt5.QtGui import QDesktopServices
import attr

from qtbooks import config

import logging

logger = logging.getLogger(__name__)


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
class TableI(object):
    id: Optional[int]

    def values(self) -> List[str]:
        return [_value_from_att(self, att) for att in attr.fields(self.__class__)]

    def columns(self) -> List[str]:
        return [att.name for att in attr.fields(self.__class__)]


@attr.s(auto_attribs=True)
class Book(TableI):
    title: str
    first_published: int = attr.ib(converter=int)
    edition: int = attr.ib(converter=int)
    added: datetime.date = attr.ib(converter=_convert_date)
    notes: str
    isbn: str

    class RelationList(list):
        def __init__(self, l: list, b: "Book") -> None:
            super().__init__(l)
            self.book = b

        def append(self, x):
            super().append(x)
            self.book.has_dirty_relations = True

        def remove(self, x):
            super().remove(x)
            self.book.has_dirty_relations = True

    def __attrs_post_init__(self) -> None:
        self.authors = []
        self.genres = []
        self.publishers = []
        self.readings = []
        self.owners = []
        self.wishlists = []
        self.has_dirty_relations = False

    @property
    def authors(self) -> List["BookAuthor"]:
        return self._authors

    @authors.setter
    def authors(self, value: List["BookAuthor"]) -> None:
        self._authors = Book.RelationList(value, self)
        self.has_dirty_relations = True

    @property
    def genres(self) -> List["BookGenre"]:
        return self._genres

    @genres.setter
    def genres(self, value: List["BookGenre"]) -> None:
        self._genres = Book.RelationList(value, self)
        self.has_dirty_relations = True

    @property
    def publishers(self) -> List["BookPublisher"]:
        return self._publishers

    @publishers.setter
    def publishers(self, value: List["BookPublisher"]) -> None:
        self._publishers = Book.RelationList(value, self)
        self.has_dirty_relations = True

    @property
    def readings(self) -> List["BookReader"]:
        return self._readings

    @readings.setter
    def readings(self, value: List["BookReader"]) -> None:
        self._readings = Book.RelationList(value, self)
        self.has_dirty_relations = True

    @property
    def owners(self) -> List["BookOwner"]:
        return self._owners

    @owners.setter
    def owners(self, value: List["BookOwner"]) -> None:
        self._owners = Book.RelationList(value, self)
        self.has_dirty_relations = True

    @property
    def wishlists(self) -> List["Wishlist"]:
        return self._wishlists

    @wishlists.setter
    def wishlists(self, value: List["Wishlist"]) -> None:
        self._wishlists = Book.RelationList(value, self)
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
class Author(TableI):
    name: str


def author_from_dict(obj: Union[str, Author]) -> Author:
    return _from_dict(Author, obj)


@attr.s(auto_attribs=True)
class Genre(TableI):
    name: str


def genre_from_dict(obj: Union[str, Genre]) -> Genre:
    return _from_dict(Genre, obj)


@attr.s(auto_attribs=True)
class Reader(TableI):
    name: str


def reader_from_dict(obj: Union[str, Reader]) -> Reader:
    return _from_dict(Reader, obj)


@attr.s(auto_attribs=True)
class Publisher(TableI):
    name: str


def publisher_from_dict(obj: Union[str, Publisher]) -> Publisher:
    return _from_dict(Publisher, obj)


@attr.s(auto_attribs=True)
class BookGenre(TableI):
    book: Book = attr.ib(converter=book_from_dict)
    genre: Genre = attr.ib(converter=genre_from_dict)


@attr.s(auto_attribs=True)
class BookAuthor(TableI):
    book: Book = attr.ib(converter=book_from_dict)
    author: Author = attr.ib(converter=author_from_dict)


@attr.s(auto_attribs=True)
class BookPublisher(TableI):
    book: Book = attr.ib(converter=book_from_dict)
    publisher: Publisher = attr.ib(converter=publisher_from_dict)


@attr.s(auto_attribs=True)
class BookReader(TableI):
    reader: Reader = attr.ib(converter=reader_from_dict)
    book: Book = attr.ib(converter=book_from_dict)
    start: datetime.date = attr.ib(converter=_convert_date)
    end: datetime.date = attr.ib(converter=_convert_date)
    read: bool = attr.ib(converter=bool)
    dropped: bool = attr.ib(converter=bool)
    rating: int = attr.ib(converter=int)
    notes: str


@attr.s(auto_attribs=True)
class BookOwner(TableI):
    book: Book = attr.ib(converter=book_from_dict)
    owner: Reader = attr.ib(converter=reader_from_dict)
    place: str
    loaned_to: str
    loaned_from: str


@attr.s(auto_attribs=True)
class Wishlist(TableI):
    reader: Reader = attr.ib(converter=reader_from_dict)
    book: Book = attr.ib(converter=book_from_dict)


TABLES = [
    Book,
    Author,
    Genre,
    Reader,
    Publisher,
    BookGenre,
    BookAuthor,
    BookPublisher,
    BookReader,
    BookOwner,
    Wishlist,
]


def _value_from_att(obj: TableI, att: attr.Attribute) -> str:
    v = getattr(obj, att.name)
    if v is None:
        return "NULL"
    elif att.type in TABLES:
        return f"{v.id}"
    elif att.type is datetime.date:
        return v.strftime("'%s'")
    elif att.type is int:
        return f"{v}"
    elif att.type is bool:
        return f"{v}"
    elif att.type is str:
        return "'{}'".format(v.replace("'", "''"))
    else:
        return f"'{v}'"


def create_db(fn: str) -> Connection:
    db = sqlite.connect(fn)
    db.row_factory = sqlite.Row

    if (
        db.execute("SELECT name from sqlite_master where name = 'Books'").fetchone()
        is None
    ):
        init_db(db)

    db.execute("PRAGMA foreign_keys = ON")
    if db.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise Exception("SQLite installation does not support foreign keys")

    return db


def init_db(db: Connection):
    def _def_col(att: attr.Attribute) -> str:
        if att.name == "id":
            return "id INTEGER PRIMARY KEY AUTOINCREMENT"
        elif att.type in TABLES:
            return f"{att.name} REFERENCES {att.type.__name__}s (id) ON DELETE CASCADE"
        else:
            return f"{att.name}"

    with db:
        for c in TABLES:
            cols = " , ".join(_def_col(att) for att in attr.fields(c))
            db.execute(f"CREATE TABLE {c.__name__}s({cols})")

        db.execute(
            """
            create view BooksView as
            select Books.id, title, Authors.authors, Genres.genres, Publishers.publishers, first_published, edition, isbn, notes, strftime('%%m/%%d/%%Y', added, 'unixepoch') as added
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
                    ) as Genres on Books.id = Genres.id left join
                    (
                    select b.id, group_concat(g.name) as publishers
                    from Books as b join BookPublishers as bg on b.id = bg.book
                                    join Publishers as g on bg.publisher = g.id
                    group by b.id
                    ) as Publishers on Books.id = Publishers.id
            """
        )


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

            insert into Books(title, first_published, edition, notes, isbn)
            values ('Tragedias I', '-406', '11', '', '9788437605456');

            insert into BookGenres(book, genre)
            values (1, 1), (1, 2);

            insert into BookAuthors(book, author)
            values (1, 1), (1, 2);

            insert into BookPublishers(book, publisher)
            values (1, 1);

            insert into BookReaders(book, reader, start, end, dropped, read, notes)
            values (1, 1, strftime('%s', date('2021-01-05')), strftime('%s', date('2021-01-10')), False, True, Null);

            insert into BookOwners(book, owner, place, loaned_to, loaned_from)
            values (1, 1, 'Living room glassdoor bookcase shelf 1', '', '');

            insert into Wishlists(reader, book)
            values (1, 1);

            """
        )

    return db


class Controller(object):
    def __init__(self, fn: str) -> None:
        # self.db = make_test_db(fn)
        self.db = create_db(fn)
        self.lockfile = Path(fn).parent / ".qtbooks.lock"
        self.readonly = not self.acquire_lock()
        self.user: Optional[Reader] = None

    def acquire_lock(self) -> bool:
        if self.lockfile.exists():
            return False
        else:
            self.lockfile.touch()
            return True

    def release_lock(self) -> None:
        if not self.readonly:
            self.lockfile.unlink(missing_ok=True)

    def execute(self, sql: str, *args, **kwargs) -> sqlite.Cursor:
        logger.debug(f"sql: {sql}")
        if self.readonly and not sql.lstrip()[:10].lower().startswith("select "):
            raise ValueError("Write query can't be executed on readonly database")
        return self.db.execute(sql, *args, **kwargs)

    def change_user(self, user_name: str) -> None:
        self.user = self.get_or_make_reader(user_name)
        if self.user.id is None:
            self._insert_obj(self.user)
        self._invalidate_caches()

    @lru_cache
    def get_view(self, view: config.View) -> Tuple[List[Row], List[str]]:
        if self.user is None:
            raise ValueError("Can't obtain view without a logged in user")
        sql = view.query.format(user=self.user.id)
        cursor = self.execute(sql)
        rows = cursor.fetchall()
        header = [t[0] for t in cursor.description]
        return rows, header

    @lru_cache
    def get_all_books(self) -> List[Row]:
        rows = self.execute(
            """
            select BooksView.id, title, authors, genres, publishers, first_published, edition, notes
            from BooksView
            """
        ).fetchall()

        return rows

    @lru_cache
    def get_book_isbn(self, isbn: str) -> Book:
        try:
            book_row = self.execute(
                "select id from Books where isbn = ?", [isbn]
            ).fetchone()
        except Exception as e:
            raise e
        if book_row is None:
            raise ValueError(f"No book found with isbn {isbn}")
        return self.get_book(book_row["id"])

    @lru_cache
    def get_books_title(self, title: str) -> List[Book]:
        try:
            book_rows = self.execute(
                "select id from Books where title = ?", [title]
            ).fetchall()
        except Exception as e:
            raise e
        return [self.get_book(row["id"]) for row in book_rows]

    @lru_cache
    def get_book(self, id: int) -> Book:
        logger.debug(f"Getting book {id}")

        try:
            book_row = self.execute("select * from Books where id = ?", [id]).fetchone()
            author_rows = self.execute(
                """select BookAuthors.id as id,
                          json_object('id', Authors.id, 'name', name) as author
                from BookAuthors join Authors on BookAuthors.author = Authors.id
                where BookAuthors.book = ?""",
                [id],
            ).fetchall()
            genre_rows = self.execute(
                """select BookGenres.id as id,
                          json_object('id', Genres.id, 'name', name) as genre
                from BookGenres join Genres on BookGenres.genre = Genres.id
                where BookGenres.book = ?""",
                [id],
            ).fetchall()
            publisher_rows = self.execute(
                """select BookPublishers.id as id,
                          json_object('id', Publishers.id, 'name', name) as publisher
                from BookPublishers join Publishers on BookPublishers.publisher = Publishers.id
                where BookPublishers.book = ?""",
                [id],
            ).fetchall()
            reading_rows = self.execute(
                """select BookReaders.id as id,
                          json_object('id', Readers.id, 'name', name) as reader,
                          start, end, dropped, read, notes, rating
                from BookReaders join Readers on BookReaders.reader = Readers.id
                where BookReaders.book = ?""",
                [id],
            ).fetchall()
            owner_rows = self.execute(
                """select BookOwners.id as id,
                          json_object('id', Readers.id, 'name', name) as owner,
                          place, loaned_to, loaned_from
                from BookOwners join Readers on BookOwners.owner = Readers.id
                where BookOwners.book = ?""",
                [id],
            ).fetchall()
            wishlist_rows = self.execute(
                """select Wishlists.id as id,
                          json_object('id', Readers.id, 'name', name) as reader
                from Wishlists join Readers on Wishlists.reader = Readers.id
                where Wishlists.book = ?""",
                [id],
            ).fetchall()
        except Exception as e:
            raise e
        book = Book(**book_row)
        logger.debug(f"{len(author_rows)}")

        book.authors = [BookAuthor(book=book, **row) for row in author_rows]
        book.genres = [BookGenre(book=book, **row) for row in genre_rows]
        book.publishers = [BookPublisher(book=book, **row) for row in publisher_rows]
        book.readings = [BookReader(book=book, **row) for row in reading_rows]
        book.owners = [BookOwner(book=book, **row) for row in owner_rows]
        book.wishlists = [Wishlist(book=book, **row) for row in wishlist_rows]
        book.has_dirty_relations = False
        return book

    def get_or_make_reader(self, name: str) -> Reader:
        row = self.execute(
            "select * from Readers where name = ? collate nocase", [name]
        ).fetchone()
        if row is None:
            reader = Reader(None, name)
        else:
            reader = Reader(**row)
        return reader

    def get_or_make_book_author(self, book: Book, name: str) -> BookAuthor:
        row = self.execute("select * from Authors where name = ?", [name]).fetchone()
        if row is None:
            author = Author(None, name)
        else:
            author = Author(**row)
        return BookAuthor(None, book=book, author=author)

    def get_or_make_book_genre(self, book: Book, name: str) -> BookGenre:
        row = self.execute("select * from Genres where name = ?", [name]).fetchone()
        if row is None:
            genre = Genre(None, name)
        else:
            genre = Genre(**row)
        return BookGenre(None, book=book, genre=genre)

    def get_or_make_book_publisher(self, book: Book, name: str) -> BookPublisher:
        row = self.execute("select * from Publishers where name = ?", [name]).fetchone()
        if row is None:
            publisher = Publisher(None, name)
        else:
            publisher = Publisher(**row)
        return BookPublisher(None, book=book, publisher=publisher)

    @lru_cache
    def get_all_authors(self) -> List[str]:
        return [r["name"] for r in self.execute("select name from Authors")]

    @lru_cache
    def get_all_genres(self) -> List[str]:
        return [r["name"] for r in self.execute("select name from Genres")]

    @lru_cache
    def get_all_publishers(self) -> List[str]:
        return [r["name"] for r in self.execute("select name from Publishers")]

    @lru_cache
    def get_all_readers(self) -> List[str]:
        return [r["name"].lower() for r in self.execute("select name from Readers")]

    def _invalidate_caches(self) -> None:
        for method_name in dir(self):
            if not method_name.startswith("_") and hasattr(
                (method := getattr(self, method_name)), "cache_clear"
            ):
                method.cache_clear()

    def update_book(self, book: Book) -> None:
        if book.has_dirty_relations:
            with self.db:
                self.delete_book(book)
                self.add_book(book)
            book.has_dirty_relations = False
        else:
            with self.db:
                self.execute(
                    f"""
                    update Books set ({" , ".join(book.columns())}) = ({" , ".join(book.values())})
                    where id = {book.id}
                    """
                )
                if len(book.readings) > 0:
                    for reading in book.readings:
                        self.execute(
                            f"""
                            update BookReaders set ({" , ".join(reading.columns())}) = ({" , ".join(reading.values())})
                            where id = {reading.id}
                            """
                        )
                if len(book.owners) > 0:
                    for owner in book.owners:
                        self.execute(
                            f"""
                            update BookOwners set ({" , ".join(owner.columns())}) = ({" , ".join(owner.values())})
                            where id = {owner.id}
                            """
                        )

        self._invalidate_caches()

    def delete_book(self, book: Book) -> None:
        self.execute("delete from Books where id = ?", [book.id])
        self.db.commit()
        self._invalidate_caches()

    def add_book(self, book: Book) -> None:
        with self.db:
            self._insert_obj(book)
            for author in book.authors:
                self.add_book_author(author)
            for genre in book.genres:
                self.add_book_genre(genre)
            for publisher in book.publishers:
                self.add_book_publisher(publisher)
            for reading in book.readings:
                self._insert_obj(reading)
            for owner in book.owners:
                self._insert_obj(owner)
            for wishlist in book.wishlists:
                self._insert_obj(wishlist)

    def add_book_author(self, item: BookAuthor) -> None:
        with self.db:
            if item.author.id is None:
                self._insert_obj(item.author)
            self._insert_obj(item)

    def add_book_genre(self, item: BookGenre) -> None:
        with self.db:
            if item.genre.id is None:
                self._insert_obj(item.genre)
            self._insert_obj(item)

    def add_book_publisher(self, item: BookPublisher) -> None:
        with self.db:
            if item.publisher.id is None:
                self._insert_obj(item.publisher)
            self._insert_obj(item)

    def add_reader(self, item: Reader) -> None:
        with self.db:
            self._insert_obj(item)

    def _insert_obj(self, obj: TableI):
        # query = f"""insert into {obj.__class__.__name__}s values ({" , ".join(obj.values())}) returning id"""
        query = f"""insert into {obj.__class__.__name__}s values ({" , ".join(obj.values())})"""
        # id = self.execute(query).fetchone()[0]
        self.execute(query)
        idquery = f"""select id from {obj.__class__.__name__}s
                      where {" and ".join(
                        f"{col} = {val}"
                        for col, val in zip(obj.columns(), obj.values())
                        if col != "id")}
                      order by id desc"""
        id = self.execute(idquery).fetchone()[0]
        obj.id = int(id)
        self.db.commit()
        self._invalidate_caches()


class RowFilter(object):
    def __init__(self, exp: str) -> None:
        self.exp = exp
        self.regexes: Dict[str, List[re.Pattern]] = dict()
        for k, v in split_tokens(exp):
            self.regexes.setdefault(k, []).append(re.compile(v, re.IGNORECASE))

    def matches(self, row: Row) -> bool:
        if "" in self.regexes:
            for regex in self.regexes[""]:
                match = False
                for v in row:
                    if regex.search(f"{v}") is not None:
                        match = True
                        break
                if not match:
                    return False

        for k, v in self.regexes.items():
            if k == "":
                continue
            if k not in row.keys():
                return False
            for regex in v:
                if regex.search(f"{row[k]}") is None:
                    return False

        return True


def split_tokens(exp: str) -> Iterator[Tuple[str, str]]:
    exp = exp + " "
    j = 0
    tagged = False
    quote_open = False
    quoted = False
    blank = True
    for i in range(len(exp)):
        if exp[i] == ":":
            if quote_open:
                continue
            if tagged:
                raise ValueError("Malformed expression: extra colon at character {i}")
            tagged = True
            correct_quote = 1 if quoted else 0
            tag = exp[j : i - correct_quote]
            j = i + 1
            quoted = False
        elif exp[i] == '"':
            if quoted:
                raise ValueError(
                    "Malformed expression: invalid character following closing quote at character {i}"
                )
            if quote_open:
                quoted = True
                quote_open = False
            else:
                quote_open = True
                j = i + 1
        elif exp[i] == " ":
            if blank:
                j = i + 1
                continue
            if quote_open:
                continue
            correct_quote = 1 if quoted else 0
            if tagged:
                yield tag, exp[j : i - correct_quote]
            else:
                yield "", exp[j : i - correct_quote]
            j = i + 1
            tagged = False
            blank = True
            quoted = False
        else:
            if quoted:
                raise ValueError(
                    "Malformed expression: invalid character following closing quote at character {i}"
                )
            blank = False


def test_split_tokens() -> None:
    exp = "foo"
    assert list(split_tokens(exp)) == [("", "foo")]

    exp = "foo bar"
    assert list(split_tokens(exp)) == [("", "foo"), ("", "bar")]

    exp = "  foo  bar  "
    assert list(split_tokens(exp)) == [("", "foo"), ("", "bar")]

    exp = "foo:bar"
    assert list(split_tokens(exp)) == [("foo", "bar")]

    exp = '"foo bar":"bar foo"'
    assert list(split_tokens(exp)) == [("foo bar", "bar foo")]

    exp = '"foo:bar":"bar foo"'
    assert list(split_tokens(exp)) == [("foo:bar", "bar foo")]
