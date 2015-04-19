# Fab deploy #

[![Travis CI Badge](https://api.travis-ci.org/illagrenan/color-printer.png)](https://travis-ci.org/illagrenan/color-printer)
&nbsp;
[![Coverage Status](https://coveralls.io/repos/illagrenan/color-printer/badge.svg?branch=master)](https://coveralls.io/r/illagrenan/color-printer?branch=master)
&nbsp;
[![Requirements Status](https://requires.io/github/illagrenan/color-printer/requirements.svg?branch=master)](https://requires.io/github/illagrenan/color-printer/requirements/?branch=master)

## Installation ##

**This package is not yet on PyPI.**

```bash
pip install --upgrade git+git://github.com/illagrenan/color-printer.git#egg=color-printer
```

## Usage ##

```bash
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
```
