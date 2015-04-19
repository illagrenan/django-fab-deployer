Fab deploy
==========

|Travis CI Badge|   |Coverage Status|   |Requirements Status|

Installation
------------

**This package is not yet on PyPI.**

.. code:: bash

    pip install --upgrade git+git://github.com/illagrenan/color-printer.git#egg=color-printer

Usage
-----

.. code:: bash

    from color_printer import colors

    # Print black
    colors.black("Foo bar")

    # Print red
    colors.red("Foo bar")

    # Print green
    colors.green("Foo bar")

    # ...
    colors.yellow("Foo bar")
    colors.blue("Foo bar")
    colors.magenta("Foo bar")
    colors.cyan("Foo bar")
    colors.white("Foo bar")

.. |Travis CI Badge| image:: https://api.travis-ci.org/illagrenan/color-printer.png
   :target: https://travis-ci.org/illagrenan/color-printer
.. |Coverage Status| image:: https://coveralls.io/repos/illagrenan/color-printer/badge.svg?branch=master
   :target: https://coveralls.io/r/illagrenan/color-printer?branch=master
.. |Requirements Status| image:: https://requires.io/github/illagrenan/color-printer/requirements.svg?branch=master
   :target: https://requires.io/github/illagrenan/color-printer/requirements/?branch=master
