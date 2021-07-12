get_version |b-pypi| |b-conda| |b-travis| |b-cover| |b-black|
=============================================================
Automatically use the latest “vX.X.X” Git tag as version in your Python package.

It also supports getting the version from Python source distributions (``sdist``) or,
once your package is installed, via ``importlib.metadata``.

usage
-----
Add the following into ``yourpackage.py`` (or ``__init__.py``):

.. code-block:: python

    from get_version import get_version
    __version__ = get_version(__file__)
    del get_version

contributing
------------
Use |black|_ to ensure proper code style. In order to not forget you can use |pre-commit|_.

.. |b-travis| image:: https://travis-ci.com/flying-sheep/get_version.svg?branch=master
   :target: https://travis-ci.com/flying-sheep/get_version
.. |b-cover| image:: https://coveralls.io/repos/github/flying-sheep/get_version/badge.svg
   :target: https://coveralls.io/github/flying-sheep/get_version
.. |b-pypi| image:: https://img.shields.io/pypi/v/get_version.svg
   :target: https://pypi.org/project/get_version
.. |b-conda| image:: https://img.shields.io/conda/vn/conda-forge/get_version.svg
   :target: https://anaconda.org/conda-forge/get_version
.. |b-black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black

.. |black| replace:: ``black .``
.. _black: https://black.readthedocs.io/en/stable/
.. |pre-commit| replace:: ``pre-commit install``
.. _pre-commit: https://pre-commit.com/
