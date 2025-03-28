# python package setup
from setuptools import setup, find_packages

setup(
    name="chromium-jumpstart",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "jumpstart=jumpstart.init:main",
        ],
    },
    install_requires=[],
)
