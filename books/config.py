import configparser
import argparse
import getpass
import json
import os

import attr

import logging

logger = logging.getLogger(__name__)


CONFIG_FILES = ["./books.cfg", "~/.books.cfg", "~/.config/books/config"]
if os.environ.get("XDG_CONFIG_HOME"):
    CONFIG_FILES.append(os.path.join(os.environ["XDG_CONFIG_HOME"], "books/config"))


@attr.s(auto_attribs=True, frozen=True)
class View(object):
    name: str
    query: str
    shortcut: str = ""
    hidden_cols: tuple[str, ...] = attr.ib(factory=tuple, converter=tuple)
    shown_cols: tuple[str, ...] = attr.ib(factory=tuple, converter=tuple)
    sort_col: str = "id"
    sort_asc: bool = True


@attr.s(auto_attribs=True)
class Options(object):
    user: str = getpass.getuser()
    db_file: str = "./books.sqlite"
    views: list[View] = attr.ib(factory=list)

    def update(self, d: dict) -> None:
        for k, v in d.items():
            if hasattr(self, k) and v is not None:
                setattr(self, k, v)


def parse_config_file(fn: str) -> Options:
    config = configparser.ConfigParser()
    config.read(fn)
    options = Options()

    options.update(dict(config["options"]))

    for k, v in config["views"].items():
        v = v.replace("\n", " ")
        options.views.append(View(name=k, **json.loads(v)))

    return options


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage book library")
    parser.add_argument("-u", "--user", help="Name of the logged in user")
    parser.add_argument("-f", "--db-file", help="Database filename")

    return parser


def parse_config() -> Options:
    for f in CONFIG_FILES:
        try:
            options = parse_config_file(f)
            break
        except FileNotFoundError:
            pass

    argparser = build_arg_parser()
    args = argparser.parse_args()
    options.update(vars(args))

    return options