from os.path import dirname, join
from setuptools import find_packages, setup


def read(path):
    with open(join(dirname(__file__), path)) as f:
        return f.read()


setup(
    name="bloc",
    version='0.1.2',
    description='Single-master group membership framework',
    long_description=read("README.rst"),
    url="https://github.com/manishtomar/bloc",

    author='Manish Tomar',
    author_email='manishtomar.public@gmail.com',
    maintainer='Manish Tomar',
    maintainer_email='manishtomar.public@gmail.com',

    license='MIT',
    keywords="group membership distributed systems",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP"
    ],
    packages=["bloc", "twisted.plugins"],
    package_dir={"": "src"},
    install_requires=[
        "twisted>=16.5.0",
        "treq>=15.1.0",
        "klein>=15.0.0"
    ]
)
