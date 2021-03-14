import sys
import datetime
from typing import Optional

from PyQt5 import QtWidgets as qtw, QtCore as qtc
from books import model


class App(qtw.QMainWindow):
    def __init__(self, controller: model.Controller) -> None:
        super().__init__()
        self.title = "Pyqtw.Qt5 simple window - pythonspot.com"
        self.left = 10
        self.top = 10
        self.w = 640
        self.h = 480
        self.controller = controller
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.w, self.h)

        self.table = Table()
        rows = self.controller.get_all_books()
        self.table.set_data(rows, rows[0].keys())
        self.table.cellDoubleClicked.connect(self.edit_book)  # type: ignore

        self.setCentralWidget(self.table)

        # bookdiag = BookDialog().exec()

        self.show()

    def edit_book(self, i: int, j: int) -> None:
        book_id = self.table.item(i, 0).text()
        bookdiag = BookDialog(self.controller, self.controller.get_book(int(book_id)))
        bookdiag.exec()
        book = bookdiag.get_book()
        print(
            f"{book}\n{book.authors}\n{book.genres}\n{book.readings}\n{book.wishlists}"
        )


class Table(qtw.QTableWidget):
    def set_data(self, data: list[tuple[str, ...]], header: tuple[str, ...]) -> None:
        self.setColumnCount(len(header))
        self.setRowCount(len(data))
        self.setHorizontalHeaderLabels(header)

        for i, row in enumerate(data):
            for j, col in enumerate(row):
                self.setItem(i, j, qtw.QTableWidgetItem(f"{col}"))


class BookDialog(qtw.QDialog):
    def __init__(
        self, controller: model.Controller, book: Optional[model.Book] = None
    ) -> None:
        super().__init__()
        self.title = (
            "Add a new book" if book is None else f"Editing book '{book.title}'"
        )
        self.left = 10
        self.top = 10
        self.w = 640
        self.h = 480
        self.book = book
        self.controller = controller
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.w, self.h)

        # Buttons
        buttons = qtw.QDialogButtonBox(
            qtw.QDialogButtonBox.Ok | qtw.QDialogButtonBox.Cancel,
        )
        buttons.accepted.connect(self.accept)  # type: ignore
        buttons.rejected.connect(self.reject)  # type: ignore
        self.buttons = buttons

        # Left form
        left_form = qtw.QFormLayout()
        self.wtitle = qtw.QLineEdit()
        left_form.addRow("Title", self.wtitle)
        self.wauthor = ComboWidget()
        left_form.addRow("Author", self.wauthor)
        self.wgenre = ComboWidget()
        left_form.addRow("Genre", self.wgenre)
        self.wfirst = qtw.QLineEdit()
        left_form.addRow("First Published", self.wfirst)
        self.wedition = qtw.QLineEdit()
        left_form.addRow("Edition", self.wedition)
        self.wnotes = qtw.QTextEdit()
        left_form.addRow("Notes", self.wnotes)
        self.left_form = left_form

        # Right form
        right_form = qtw.QFormLayout()
        self.wread = qtw.QCheckBox()
        self.wread.stateChanged.connect(self.read_changed)  # type: ignore
        right_form.addRow("Read", self.wread)

        self.wstart = qtw.QDateEdit(qtc.QDate.currentDate())
        self.wstart.setCalendarPopup(True)
        self.wend = qtw.QDateEdit(qtc.QDate.currentDate())
        self.wend.setCalendarPopup(True)
        right_form.addRow("Start", self.wstart)
        right_form.addRow("End", self.wend)
        self.wdropped = qtw.QCheckBox()
        right_form.addRow("Dropped", self.wdropped)
        self.wreadnotes = qtw.QTextEdit()
        right_form.addRow("Notes", self.wreadnotes)
        self.read_widgets = [self.wstart, self.wend, self.wdropped, self.wreadnotes]
        self.set_read_widgets_enabled(False)

        self.wwtr = qtw.QCheckBox()
        right_form.addRow("Want to read", self.wwtr)
        self.right_form = right_form

        # Forms
        forms = qtw.QHBoxLayout()
        forms.addLayout(left_form)
        forms.addSpacing(20)
        forms.addLayout(right_form)
        self.forms = forms

        # Top layout
        top_layout = qtw.QVBoxLayout(self)
        top_layout.addLayout(forms)
        top_layout.addWidget(buttons)
        self.setLayout(top_layout)

        self.update_data()
        self.show()

    def set_read_widgets_enabled(self, enable: bool):
        for w in self.read_widgets:
            w.setEnabled(enable)

    def read_changed(self):
        self.set_read_widgets_enabled(self.wread.isChecked())

    def get_book(self) -> model.Book:
        title = self.wtitle.text()
        firstpub = int(self.wfirst.text())
        edition = int(self.wedition.text())
        notes = self.wnotes.toPlainText()

        authors = self.wauthor.get_all()
        genres = self.wgenre.get_all()

        read = self.wread.isChecked()
        start = self.wstart.date().toPyDate()
        end = self.wend.date().toPyDate()
        dropped = self.wdropped.isChecked()
        read_notes = self.wreadnotes.toPlainText()

        toread = self.wwtr.isChecked()

        if self.book is not None:
            book = self.book
            book.title = title
            book.first_published = firstpub
            book.edition = edition
            book.notes = notes
        else:
            added = datetime.date.today()
            book = model.Book(-1, title, firstpub, edition, added, notes)

        if len(authors) != len(book.authors) or any(
            a != b.author.name for a, b in zip(authors, book.authors)
        ):
            book.authors = [
                self.controller.get_or_make_book_author(book, name) for name in authors
            ]

        if len(genres) != len(book.genres) or any(
            a != b.genre.name for a, b in zip(genres, book.genres)
        ):
            book.genres = [
                self.controller.get_or_make_book_genre(book, name) for name in genres
            ]

        if read:
            if len(book.readings) == 1:
                book.readings[0].start = start
                book.readings[0].end = end
                book.readings[0].dropped = dropped
                book.readings[0].notes = read_notes
            else:
                book.readings = [
                    model.BookReader(
                        -1, self.controller.user, book, start, end, dropped, read_notes
                    )
                ]
        elif len(book.readings) == 1:
            book.readings = []

        if toread and len(book.wishlists) == 0:
            book.wishlists = [model.Wishlist(-1, self.controller.user, book)]
        elif not toread and len(book.wishlists) == 1:
            book.wishlists = []

        return book

    def update_data(self) -> None:
        if self.book is None:
            return

        self.wtitle.setText(self.book.title)
        self.wfirst.setText(f"{self.book.first_published}")
        self.wedition.setText(f"{self.book.edition}")
        self.wnotes.setText(self.book.notes)

        self.wauthor.clear()
        if len(self.book.authors) == 0:
            self.wauthor.make_combo("")
        else:
            for author in self.book.authors:
                self.wauthor.make_combo(author.author.name)
        self.wgenre.clear()
        if len(self.book.genres) == 0:
            self.wgenre.make_combo("")
        else:
            for genre in self.book.genres:
                self.wgenre.make_combo(genre.genre.name)

        try:
            reading = next(
                r for r in self.book.readings if self.controller.user.id == r.reader.id
            )
            self.wread.setChecked(True)
            self.wstart.setDate(reading.start)
            self.wend.setDate(reading.end)
            self.wdropped.setChecked(reading.dropped)
            self.wreadnotes.setText(reading.notes)
        except StopIteration:
            pass
        except:
            raise

        try:
            wishlist = next(
                r for r in self.book.wishlists if self.controller.user.id == r.reader.id
            )
            self.wwtr.setChecked(True)
        except StopIteration:
            pass
        except:
            raise


class ComboWidget(qtw.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.add = qtw.QPushButton("+")
        self.add.clicked.connect(lambda x: self.make_combo())  # type: ignore
        self.add.setFixedSize(22, 22)
        self.addgroup = qtw.QVBoxLayout()
        self.addgroup.addWidget(self.add)
        # addgroup.addStretch()
        self.addgroup.setAlignment(qtc.Qt.AlignTop)  # type: ignore
        self.addgroup.setSpacing(0)
        self.addgroup.setContentsMargins(0, 0, 0, 0)

        self.combos = qtw.QVBoxLayout()

        layout = qtw.QHBoxLayout()
        layout.addLayout(self.combos)
        layout.addLayout(self.addgroup)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def clear(self) -> None:
        while self.combos.takeAt(0):
            pass

    def get_all(self) -> list[str]:
        return [
            self.combos.itemAt(i).widget().layout().itemAt(0).widget().currentText()
            for i in range(self.combos.count())
        ]

    def make_combo(self, text: str = "") -> None:
        combo_widget = qtw.QWidget()
        combo = qtw.QComboBox()
        combo.setEditable(True)
        combo.setCurrentText(text)
        remove = qtw.QPushButton("-")
        remove.setFixedSize(22, 22)

        layout = qtw.QHBoxLayout()
        layout.addWidget(combo)
        layout.addWidget(remove)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        combo_widget.setLayout(layout)

        def rem(x):
            if self.combos.count() > 1:
                self.combos.removeWidget(combo_widget)
                qtw.QWidget().setLayout(layout)
            else:
                combo.setCurrentText("")

        remove.clicked.connect(rem)  # type: ignore
        self.combos.addWidget(combo_widget)


def main() -> None:
    app = qtw.QApplication(sys.argv)
    controller = model.Controller("test.db", 1)
    window = App(controller)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
