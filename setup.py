from setuptools import setup, find_packages

config = {
    "description": "",
    "url": "",
    "author": "Fran Penedo",
    "author_email": "fran@franpenedo.com",
    "version": "0.0.1",
    "install_requires": [
        "attrs>=21.2.0",
        "beautifulsoup4>=4.10.0",
        "pyqt5>=5.15.6",
        "requests>=2.26.0",
        "click>=8.0.3",
    ],
    "extras_require": {},
    "packages": find_packages(),
    "scripts": [],
    "name": "books",
}

setup(**config)
