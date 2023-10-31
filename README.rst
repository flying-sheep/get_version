get_version |b-pypi| |b-conda| |b-ci| |b-cover|
===============================================
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

.. |b-ci| image:: https://github.com/flying-sheep/get_version/actions/workflows/run_tests.yml/badge.svg
   :target: https://github.com/flying-sheep/get_version/actions/workflows/run_tests.yml
.. |b-cover| image:: https://coveralls.io/repos/github/flying-sheep/get_version/badge.svg
   :target: https://coveralls.io/github/flying-sheep/get_version
.. |b-pypi| image:: https://img.shields.io/pypi/v/get_version.svg
   :target: https://pypi.org/project/get_version
.. |b-conda| image:: https://img.shields.io/conda/vn/conda-forge/get_version.svg
   :target: https://anaconda.org/conda-forge/get_version
