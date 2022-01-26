import traceback
import csv
from datetime import datetime
from typing import Optional

import click

from qtbooks import model, extract


@click.command()
@click.option(
    "-i",
    "--input-csv",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
)
@click.option(
    "-o", "--output-db", type=click.Path(dir_okay=False, writable=True), required=True
)
@click.option("-u", "--user", type=str, required=True)
@click.option("--out-csv", type=click.Path(dir_okay=False, writable=True))
def import_books(
    output_db: str, input_csv: str, user: str, out_csv: Optional[str]
) -> None:
    controller = model.Controller(output_db)
    controller.change_user(user)

    with open(input_csv) as f:
        library = list(csv.reader(f, delimiter=","))

    lib = [{key: value for key, value in zip(library[0], row)} for row in library[1:]]

    gr_failed = []
    import_failed = []
    for entry in lib:
        try:
            book = extract.import_book(
                f"https://goodreads.com/book/show/{entry['Book Id']}", controller
            )
        except ConnectionError as e:
            print(f"Failed to obtain goodreads page for book {entry['Title']}")
            gr_failed.append(entry)
            continue
        except Exception as e:
            print(f"Book {entry['Title']} couldn't be imported")
            print(traceback.format_exc())
            import_failed.append(entry)
            continue

        if entry["Exclusive Shelf"] == "read":
            date = datetime.strptime(
                entry["Date Read"] or entry["Date Added"], "%Y/%m/%d"
            )

            book.readings.append(
                model.BookReader(
                    None, controller.user, book, date, date, True, False, ""
                )
            )
        elif entry["Exclusive Shelf"] == "to-read":
            book.wishlists.append(model.Wishlist(None, controller.user, book))
        else:
            print(f"Book {entry['Title']} wasn't read or wtr")
            print(entry)

        controller.add_book(book)
        print(f"Imported {entry['Title']}")

    print(f"Failed to import: {[entry['Title'] for entry in import_failed]}")
    print(f"Failed to get goodreads page: {[entry['Title'] for entry in gr_failed]}")
    if out_csv is not None:
        with open(out_csv, "w") as f:
            csv_writer = csv.writer(f, delimiter=",")
            csv_writer.writerow(library[0])
            csv_writer.writerows(entry.values() for entry in gr_failed)


if __name__ == "__main__":
    import logging
    import logging.config
    from qtbooks import LOGGER_DEBUG_CONFIG

    logging.config.dictConfig(LOGGER_DEBUG_CONFIG)
    logging.getLogger("qtbooks").setLevel(logging.WARNING)
    import_books()
