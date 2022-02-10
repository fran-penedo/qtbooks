from setuptools import setup, find_packages

config = {
    "description": "",
    "url": "",
    "author": "Fran Penedo",
    "author_email": "fran@franpenedo.com",
    "version": "0.0.2",
    "install_requires": [
        "attrs>=21.2.0",
        "beautifulsoup4>=4.10.0",
        "pyqt5>=5.15.6",
        "requests>=2.26.0",
        "click>=8.0.3",
        "lxml>=4.7.1",
    ],
    "extras_require": {},
    "packages": find_packages(),
    "package_data": {"qtbooks": ["../qtbooks.cfg", "../resources/bookshelf.png"]},
    "scripts": [],
    "entry_points": {"console_scripts": ["qtbooks=qtbooks.cli:cli"]},
    "name": "qtbooks",
}

setup(**config)
