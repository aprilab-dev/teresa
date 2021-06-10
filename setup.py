
from setuptools import setup, find_packages

with open("README.md") as fp:
    readme = fp.read()

# https://packaging.python.org/guides/single-sourcing-package-version/
version_info = {}
with open("teresa/version.py") as fp:
    exec(fp.read(), version_info)

# dependencies
with open("requirements.txt") as fp:
    install_requires = fp.read()
tests_require=[   # tests
    "pytest",
    "pytest-cov"
]
docs_require=[ # docs 
    "sphinx",
]

setup(
    name="teresa",
    version=version_info["__version__"],
    description="[TE]rraquanta's software for [RE]gistration and [SA]mpling",
    long_description=readme,
    author="TerraQuanta",
    url="https://git.terraqt.dev/dev.fringe/teresa",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=install_requires,
    setup_requires=["pytest-runner", "flake8"],
    tests_require=tests_require,
    extras_require={
	"test": tests_require, 
	"doc": docs_require
    },
)

