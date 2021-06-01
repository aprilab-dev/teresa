
from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

# https://packaging.python.org/guides/single-sourcing-package-version/
version_info = {}
with open("teresa/version.py") as file:
    exec(file.read(), version_info)


setup(
    name="teresa",
    version=version_info["__version__"],
    description="TErraquanta's software for REgistration and SAmpling.",
    long_description=readme,
    author="TerraQuanta",
    url="https://git.terraqt.dev/dev.fringe/teresa",
    packages=find_packages(exclude=('tests', 'docs'))
)

