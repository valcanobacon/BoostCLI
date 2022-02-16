#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
    name="BoostCLI",
    version="0.1.1",
    python_requires=">=3.9",
    description="Boost CLI",
    author_email="boostcli.v1pty@slmail.me",
    packages=find_packages(include=["src", "src.*"]),
    entry_points={
        "console_scripts": [
            "boostcli=src.cli:cli",
        ],
    },
    install_requires=[
        "lnd-grpc-client<1,>=0.3.39",
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
    ],
    extras_require={
        "tests": ["pytest>=6.2.5,<7"],
    },
)
