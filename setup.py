#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="string-search-server",
    version="1.0.0",
    description="High-performance string search server",
    author="Phinehas Macharia",
    author_email="walburphinehas78@gmail.com",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.0",
        "pytest>=7.0.0",
        "rich>=10.0.0",
    ],
    python_requires=">=3.8",
) 