from os.path import dirname, join
from setuptools import find_packages, setup

package_name = "bloc"

def read(path):
    with open(join(dirname(__file__), path)) as f:
        return f.read()

setup(name=package_name,
      version='0.0.1',
      description='Single-master group membership service',
      long_description=read("README.rst"),
      url="https://github.com/manishtomar/bloc",

      author='Manish Tomar',
      author_email='manish.tomar@gmail.com',
      maintainer='Manish Tomar',
      maintainer_email='manish.tomar@gmail.com',

      license='MIT',
      keywords="group membership distributed systems",
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Natural Language :: English",
          "Programming Language :: Python :: 2 :: Only",
          "Programming Language :: Python :: 2.7",
          "Topic :: Internet :: WWW/HTTP"
      ],
      packages=["bloc"],
      package_dir={"": "src"},
      install_requires=[
          "twisted>=16.0.0",
          "treq>=15.1.0",
          "klein>=15.0.0"
      ]
      )