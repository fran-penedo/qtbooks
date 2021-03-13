import sqlite3 as sqlite
from sqlite3 import Connection, Row
import datetime
import os

import attr


@attr.s(auto_attribs=True)
class Book(object):
    id: int
    title: str
    first_published: int
    edition: int
    added: datetime.date
    notes: str

    @property
    def authors(self) -> list["Author"]:
        return self._authors

    @authors.setter
    def authors(self, value: list["Author"]) -> None:
        self._authors = value

    @property
    def genres(self) -> list["Genre"]:
        return self._genres

    @genres.setter
    def genres(self, value: list["Genre"]) -> None:
        self._genres = value

    @property
    def readers(self) -> list["Reader"]:
        return self._readers

    @readers.setter
    def readers(self, value: list["Reader"]) -> None:
        self._readers = value


@attr.s(auto_attribs=True)
class Author(object):
    id: int
    name: str


@attr.s(auto_attribs=True)
class Genre(object):
    id: int
    name: str


@attr.s(auto_attribs=True)
class Reader(object):
    id: int
    name: str


@attr.s(auto_attribs=True)
class Publisher(object):
    id: int
    name: str


@attr.s(auto_attribs=True)
class BookGenre(object):
    id: int
    book: Book
    genre: Genre


@attr.s(auto_attribs=True)
class BookAuthor(object):
    id: int
    book: Book
    author: Author


@attr.s(auto_attribs=True)
class BookReader(object):
    id: int
    reader: Reader
    book: Book
    start: datetime.date
    end: datetime.date
    dropped: bool
    notes: str


@attr.s(auto_attribs=True)
class Wishlist(object):
    id: int
    reader: Reader
    book: Book


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

            """
        )

    return db


class Controller(object):
    def __init__(self, fn: str) -> None:
        self.db = create_db(fn)

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
                """select Authors.id as id, name
                from BookAuthors join Authors on BookAuthors.author = Authors.id
                where BookAuthors.book = ?""",
                [id],
            ).fetchall()
            genre_rows = self.db.execute(
                """select Genres.id as id, name
                from BookGenres join Genres on BookGenres.genre = Genres.id
                where BookGenres.book = ?""",
                [id],
            ).fetchall()
            reader_rows = self.db.execute(
                """select Readers.id as id, name
                from BookReaders join Readers on BookReaders.reader = Readers.id
                where BookReaders.book = ?""",
                [id],
            ).fetchall()
        except Exception as e:
            raise e
        book = Book(**book_row)
        book.authors = [Author(**row) for row in author_rows]
        book.genres = [Genre(**row) for row in genre_rows]
        book.readers = [Reader(**row) for row in reader_rows]
        return book
