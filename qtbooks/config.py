import configparser
from pkg_resources import resource_filename
import getpass
import json
import os

import attr

import logging

logger = logging.getLogger(__name__)


CONFIG_FILES = ["~/.config/qtbooks/config", "~/.qtbooks.cfg", "./qtbooks.cfg"]
if os.environ.get("XDG_CONFIG_HOME"):
    CONFIG_FILES.insert(
        0, os.path.join(os.environ["XDG_CONFIG_HOME"], "qtbooks/config")
    )


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
    db_file: str = "./qtbooks.sqlite"
    views: list[View] = attr.ib(factory=list)
    verbose: bool = False

    def update(self, d: dict) -> None:
        for k, v in d.items():
            if hasattr(self, k) and v is not None:
                setattr(self, k, v)


def parse_config_files(fns: list[str]) -> Options:
    config = configparser.ConfigParser()
    config.read_file(open(resource_filename("qtbooks", "../qtbooks.cfg")))
    config.read(fns)
    options = Options()

    options.update(dict(config["options"]))

    for k, v in config["views"].items():
        v = v.replace("\n", " ")
        options.views.append(View(name=k, **json.loads(v)))

    return options


def parse_config(args: dict) -> Options:
    if args["config"] is not None:
        CONFIG_FILES.append(args["config"])
    options = parse_config_files(CONFIG_FILES)

    options.update(args)

    return options
