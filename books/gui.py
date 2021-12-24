import sys
import datetime
from typing import Optional
import traceback

from PyQt5 import QtWidgets as qtw, QtCore as qtc, QtGui as qtg
from books import model, config, extract

import logging

logger = logging.getLogger(__name__)


class App(qtw.QMainWindow):
    def __init__(self, controller: model.Controller, options: config.Options) -> None:
        super().__init__()
        self.title = "Pyqtw.Qt5 simple window - pythonspot.com"
        self.left = 10
        self.top = 10
        self.w = 640
        self.h = 480
        self.controller = controller
        self.options = options
        self.view_pages: list[Table] = []
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.w, self.h)
        self.set_shortcuts()

        self.show()

        if self.options.user.lower() in self.controller.get_all_readers():
            self.controller.change_user(self.options.user)
        else:
            self.select_user()

        self.tabs = qtw.QTabWidget()
        for view in self.options.views:
            view_page = Table(view, self.controller)
            view_page.cellDoubleClicked.connect(self.edit_book)  # type: ignore
            self.view_pages.append(view_page)
            self.tabs.addTab(view_page, f"{view.shortcut}: {view.name}")
            shortcut = qtw.QShortcut(qtg.QKeySequence(view.shortcut), self)
            shortcut.activated.connect(  # type: ignore
                lambda w=view_page: self.tabs.setCurrentWidget(w)
            )

        self.setCentralWidget(self.tabs)

    def edit_book(self, i: int, j: int) -> None:
        try:
            book_id = self.sender().rows[i]["id"]
        except ValueError:
            return
        bookdiag = BookDialog(self.controller, self.controller.get_book(int(book_id)))
        if bookdiag.exec() == qtw.QDialog.Accepted:
            book = bookdiag.get_book()
            self.controller.update_book(book)
            self.update_tables()

    def add_book(self) -> None:
        bookdiag = BookDialog(self.controller)
        if bookdiag.exec() == qtw.QDialog.Accepted:
            book = bookdiag.get_book()
            self.controller.add_book(book)
            self.update_tables()

    def update_tables(self) -> None:
        for t in self.view_pages:
            t.update_table()

    def set_shortcuts(self) -> None:
        add_new_book = qtw.QShortcut(qtg.QKeySequence("a"), self)
        add_new_book.activated.connect(self.add_book)  # type: ignore
        select_user = qtw.QShortcut(qtg.QKeySequence("u"), self)
        select_user.activated.connect(self.select_user)  # type: ignore
        import_from_url = qtw.QShortcut(qtg.QKeySequence("i"), self)
        import_from_url.activated.connect(self.import_from_url)  # type: ignore

    def select_user(self) -> None:
        selected = False
        users = self.controller.get_all_readers()
        if self.controller.user is not None:
            current = users.index(self.controller.user.name.lower())

        while not selected:
            name, ok = qtw.QInputDialog.getItem(
                self, "Select user", "User", users, current=current, editable=True
            )
            if ok:
                if name.lower() in users:
                    selected = True
                else:
                    created = qtw.QMessageBox.question(
                        self,
                        "New user",
                        f"User '{name}' does not exist. Would you like to create it?",
                    )
                    if created == qtw.QMessageBox.StandardButton.Yes:
                        selected = True

        self.controller.change_user(name)
        self.update_tables()

    def import_from_url(self) -> None:
        urls, ok = qtw.QInputDialog.getMultiLineText(
            self, "Import from url", "URL list, one per line", ""
        )
        if ok:
            for url in urls.splitlines():
                if url == "":
                    continue
                try:
                    book = extract.import_book(url, self.controller)
                    self.controller.add_book(book)
                except Exception as e:
                    qtw.QMessageBox.warning(
                        self,
                        "Unable to import",
                        f"Could not import book at url {url}: \n{traceback.format_exc()}",
                    )

        self.update_tables()


class Table(qtw.QTableWidget):
    def __init__(self, view: config.View, controller: model.Controller) -> None:
        super().__init__()
        self.view = view
        self.controller = controller
        rows, header = self.controller.get_view(self.view)

        self.rows = rows
        self.shown = [h for h in header if h not in self.view.hidden_cols]
        self.setColumnCount(len(self.shown))
        self.setHorizontalHeaderLabels(self.shown)
        self.sort_column = (
            self.shown.index(view.sort_col) if view.sort_col in self.shown else -1
        )
        self.update_table()

    def update_table(self) -> None:
        rows, _ = self.controller.get_view(self.view)
        self.rows = rows
        self.setRowCount(len(rows))

        for i, row in enumerate(rows):
            for j, col_name in enumerate(self.shown):
                self.setItem(i, j, qtw.QTableWidgetItem(f"{row[col_name]}"))

        if self.sort_column > -1:
            self.sortItems(
                self.sort_column,
                qtc.Qt.SortOrder.AscendingOrder
                if self.view.sort_asc
                else qtc.Qt.SortOrder.DescendingOrder,
            )


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
        self.wisbn = qtw.QLineEdit()
        self.wisbn.setValidator(qtg.QRegExpValidator(qtc.QRegExp(r"\d{9,13}"), self))
        self.wisbn.setText("000000000")
        left_form.addRow("ISBN", self.wisbn)
        self.wauthor = ComboWidget(self.controller.get_all_authors())
        self.wauthor.combobox_made.connect(self.set_tab_order)
        left_form.addRow("Author", self.wauthor)
        self.wgenre = ComboWidget(self.controller.get_all_genres())
        self.wgenre.combobox_made.connect(self.set_tab_order)
        left_form.addRow("Genre", self.wgenre)
        self.wpublisher = ComboWidget(self.controller.get_all_publishers())
        self.wpublisher.combobox_made.connect(self.set_tab_order)
        left_form.addRow("Publisher", self.wpublisher)
        self.wfirst = qtw.QSpinBox()
        self.wfirst.setMinimum(-5000)
        self.wfirst.setMaximum(5000)
        self.wfirst.setValue(datetime.date.today().year)
        left_form.addRow("First Published", self.wfirst)
        self.wedition = qtw.QSpinBox()
        self.wedition.setValue(1)
        left_form.addRow("Edition", self.wedition)
        self.wnotes = qtw.QTextEdit()
        self.wnotes.setTabChangesFocus(True)
        left_form.addRow("Notes", self.wnotes)
        self.left_form = left_form

        # Right form

        # Reading/wishlist form
        right_form = qtw.QFormLayout()
        self.wread = qtw.QCheckBox()
        self.wread.stateChanged.connect(self.read_changed)  # type: ignore
        right_form.addRow("Reading", self.wread)

        self.wstart = qtw.QDateEdit(qtc.QDate.currentDate())
        self.wstart.setCalendarPopup(True)
        self.wend = qtw.QDateEdit(qtc.QDate.currentDate())
        self.wend.setCalendarPopup(True)
        right_form.addRow("Start", self.wstart)
        self.wfinished = qtw.QCheckBox()
        self.wfinished.stateChanged.connect(self.read_changed)  # type: ignore
        right_form.addRow("Finished", self.wfinished)
        self.wdropped = qtw.QCheckBox()
        self.wdropped.stateChanged.connect(self.read_changed)  # type: ignore
        right_form.addRow("Dropped", self.wdropped)
        right_form.addRow("End", self.wend)
        self.wreadnotes = qtw.QTextEdit()
        self.wreadnotes.setTabChangesFocus(True)
        right_form.addRow("Notes", self.wreadnotes)
        self.read_widgets = [
            self.wstart,
            self.wend,
            self.wfinished,
            self.wdropped,
            self.wreadnotes,
        ]
        self.set_read_widgets_enabled(False)

        self.wwtr = qtw.QCheckBox()
        right_form.addRow("Want to read", self.wwtr)

        # Owner form
        self.wowned = qtw.QCheckBox()
        self.wowned.stateChanged.connect(self.owned_changed)  # type: ignore
        right_form.addRow("Owned", self.wowned)
        self.wplace = qtw.QLineEdit()
        right_form.addRow("Place", self.wplace)
        self.wloanedto = qtw.QLineEdit()
        right_form.addRow("Loaned to", self.wloanedto)
        self.wloanedfrom = qtw.QLineEdit()
        right_form.addRow("Loaned from", self.wloanedfrom)
        self.owned_widgets = [
            self.wplace,
            self.wloanedto,
            self.wloanedfrom,
        ]
        self.set_owned_widgets_enabled(False)
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
        self.set_tab_order()
        self.show()

    def set_tab_order(self) -> None:
        order = [
            self.wtitle,
            self.wisbn,
            *self.wauthor.get_all_combos(),
            *self.wgenre.get_all_combos(),
            *self.wpublisher.get_all_combos(),
            self.wfirst,
            self.wedition,
            self.wnotes,
            self.wread,
            self.wstart,
            self.wfinished,
            self.wdropped,
            self.wend,
            self.wreadnotes,
            self.wwtr,
            self.wowned,
            self.wplace,
            self.wloanedto,
            self.wloanedfrom,
            self.buttons,
        ]

        for i in range(len(order) - 1):
            qtw.QWidget.setTabOrder(order[i], order[i + 1])  # type: ignore

    def set_read_widgets_enabled(self, enable: bool) -> None:
        for w in self.read_widgets:
            w.setEnabled(enable)

    def read_changed(self) -> None:
        self.set_read_widgets_enabled(self.wread.isChecked())
        self.wend.setEnabled(
            self.wread.isChecked()
            and (self.wdropped.isChecked() or self.wfinished.isChecked())
        )

    def set_owned_widgets_enabled(self, enable: bool) -> None:
        for w in self.owned_widgets:
            w.setEnabled(enable)

    def owned_changed(self) -> None:
        self.set_owned_widgets_enabled(self.wowned.isChecked())

    def get_book(self) -> model.Book:
        title = self.wtitle.text()
        isbn = int(self.wisbn.text())
        firstpub = self.wfirst.value()
        edition = self.wedition.value()
        notes = self.wnotes.toPlainText()

        authors = self.wauthor.get_all()
        genres = self.wgenre.get_all()
        publishers = self.wpublisher.get_all()

        read = self.wread.isChecked()
        start = self.wstart.date().toPyDate()
        end = self.wend.date().toPyDate()
        finished = self.wfinished.isChecked()
        dropped = self.wdropped.isChecked()
        read_notes = self.wreadnotes.toPlainText()

        toread = self.wwtr.isChecked()

        owned = self.wowned.isChecked()
        place = self.wplace.text()
        loaned_to = self.wloanedto.text()
        loaned_from = self.wloanedfrom.text()

        if self.book is not None:
            book = self.book
            book.title = title
            book.first_published = firstpub
            book.edition = edition
            book.notes = notes
            book.isbn = isbn
        else:
            added = datetime.date.today()
            book = model.Book(None, title, firstpub, edition, added, notes, isbn)

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

        if len(publishers) != len(book.publishers) or any(
            a != b.publisher.name for a, b in zip(publishers, book.publishers)
        ):
            book.publishers = [
                self.controller.get_or_make_book_publisher(book, name)
                for name in publishers
            ]

        reading = next(
            (o for o in book.readings if o.reader.id == self.controller.user.id), None
        )
        if reading is not None and read:
            reading.start = start
            reading.end = end
            reading.read = finished
            reading.dropped = dropped
            reading.notes = read_notes
        elif reading is not None and not read:
            book.readings.remove(reading)
        elif read:
            book.readings.append(
                model.BookReader(
                    None,
                    self.controller.user,
                    book,
                    start,
                    end,
                    finished,
                    dropped,
                    read_notes,
                )
            )

        wishlist = next(
            (o for o in book.wishlists if o.reader.id == self.controller.user.id), None
        )
        if wishlist is not None and not toread:
            book.wishlists.remove(wishlist)
        elif toread and wishlist is None:
            book.wishlists.append(model.Wishlist(None, self.controller.user, book))

        owner = next(
            (o for o in book.owners if o.owner.id == self.controller.user.id), None
        )
        if owner is not None and owned:
            owner.place = place
            owner.loaned_from = loaned_from
            owner.loaned_to = loaned_to
        elif owner is not None and not owned:
            book.owners.remove(owner)
        elif owned:
            book.owners.append(
                model.BookOwner(
                    None,
                    book,
                    self.controller.user,
                    place,
                    loaned_to,
                    loaned_from,
                )
            )

        return book

    def update_data(self) -> None:
        if self.book is None:
            self.wauthor.make_combo("")
            self.wgenre.make_combo("")
            self.wpublisher.make_combo("")
            return

        self.wtitle.setText(self.book.title)
        self.wisbn.setText(str(self.book.isbn))
        self.wfirst.setValue(self.book.first_published)
        self.wedition.setValue(self.book.edition)
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
        self.wpublisher.clear()
        if len(self.book.publishers) == 0:
            self.wpublisher.make_combo("")
        else:
            for publisher in self.book.publishers:
                self.wpublisher.make_combo(publisher.publisher.name)

        reading = next(
            (r for r in self.book.readings if self.controller.user.id == r.reader.id),
            None,
        )
        if reading is not None:
            self.wread.setChecked(True)
            self.wstart.setDate(reading.start)
            self.wend.setDate(reading.end)
            self.wdropped.setChecked(reading.dropped)
            self.wfinished.setChecked(reading.read)
            self.wreadnotes.setText(reading.notes)

        owner = next(
            (o for o in self.book.owners if self.controller.user.id == o.owner.id), None
        )
        if owner is not None:
            self.wowned.setChecked(True)
            self.wplace.setText(owner.place)
            self.wloanedto.setText(owner.loaned_to)
            self.wloanedfrom.setText(owner.loaned_from)

        wishlist = next(
            (r for r in self.book.wishlists if self.controller.user.id == r.reader.id),
            None,
        )
        if wishlist is not None:
            self.wwtr.setChecked(True)


class ComboWidget(qtw.QWidget):
    combobox_made = qtc.pyqtSignal()

    def __init__(self, options: list[str]) -> None:
        super().__init__()
        self.options = options

        self.add = qtw.QPushButton("+")
        self.add.clicked.connect(lambda x: self.make_combo())  # type: ignore
        self.add.setFixedSize(22, 22)
        self.add.setFocusPolicy(qtc.Qt.FocusPolicy.ClickFocus)
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
        return [c.currentText() for c in self.get_all_combos() if c.currentText() != ""]

    def get_all_combos(self) -> list[qtw.QComboBox]:
        return [
            self.combos.itemAt(i).widget().combo for i in range(self.combos.count())
        ]

    class ComboBox(qtw.QComboBox):
        def __init__(self, widget: "ComboWidget", *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.combo_widget = widget

        def keyPressEvent(self, e: qtg.QKeyEvent) -> None:
            if e.matches(qtg.QKeySequence.StandardKey.InsertLineSeparator):
                self.combo_widget.make_combo(focus=True)
            else:
                super().keyPressEvent(e)

    def make_combo(self, text: str = "", focus: bool = False) -> None:
        combo_widget = qtw.QWidget()
        combo = ComboWidget.ComboBox(self)
        combo.insertItems(0, self.options)
        combo.setEditable(True)
        combo.setCurrentText(text)
        remove = qtw.QPushButton("-")
        remove.setFixedSize(22, 22)
        remove.setFocusPolicy(qtc.Qt.FocusPolicy.ClickFocus)

        layout = qtw.QHBoxLayout()
        layout.addWidget(combo)
        layout.addWidget(remove)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        combo_widget.setLayout(layout)
        combo_widget.combo = combo
        combo_widget.remove = remove

        def rem(x):
            if self.combos.count() > 1:
                self.combos.removeWidget(combo_widget)
                qtw.QWidget().setLayout(layout)
            else:
                combo.setCurrentText("")

        remove.clicked.connect(rem)  # type: ignore
        self.combos.addWidget(combo_widget)
        if focus:
            combo.setFocus()
        self.combobox_made.emit()


def main(args: dict) -> None:
    import logging.config
    from books import LOGGER_DEBUG_CONFIG

    logging.config.dictConfig(LOGGER_DEBUG_CONFIG)

    options = config.parse_config(args)
    app = qtw.QApplication(sys.argv)
    controller = model.Controller(options.db_file)

    window = App(controller, options)
    sys.exit(app.exec_())
