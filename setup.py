from setuptools import setup

setup(
    name="teresa",
    version="0.1.0",
    packages=["teresa"],
    install_requires=["click"],
    entry_points={
        "console_scripts": [
            "teresa = teresa.cli:coregister",
        ]
    },
)