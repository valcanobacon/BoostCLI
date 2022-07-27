#!/usr/bin/env python3

from setuptools import find_packages, setup

# read the contents of your README file
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="BoostCLI",
    version="0.4.0",
    python_requires=">=3.7",
    description="Command line tool to send and receive Podcasting 2.0 Value",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author_email="boostcli.v1pty@slmail.me",
    packages=find_packages(include=["src", "src.*"]),
    entry_points={
        "console_scripts": [
            "boostcli=src.cli:cli",
        ],
    },
    install_requires=[
        "lnd-grpc-client<3,>=2.0.0",
        "click<9,>=8.0.3",
        "beautifulsoup4<5,>=4.10.0",
        "lxml<5,>=4.7.1",
        "googleapis-common-protos<2,>=1.53.0",
        "grpcio<2,>=1.41.1",
        "grpcio-tools<2,>=1.41.1",
        "protobuf<4,>=3.19.1",
        "requests<3,>=2.27.1",
        "tabulate<1,>=0.8.9",
        "tqdm<5,>=4.62.3",
        "rich<13,>=12.5.1",
    ],
    extras_require={
        "tests": [
            "pytest<7,>=6.2.5",
            "flake8<5,>=4.0.1",
            "flake8-black<1,>=0.3.2",
        ],
        "deploy": [
            "build<1,>=0.8.0",
            "twine<5,>=4.0.1",
        ],
    },
)
