"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import os
import sys

# pylint: disable=invalid-name,redefined-builtin

sys.path.insert(0, os.path.abspath("../"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "tradingview-scraper"
copyright = "2025, Mostafa Najmi"  # noqa: A001
author = "Mostafa Najmi"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx_rtd_theme", "sphinx.ext.autodoc", "sphinx.ext.viewcode"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]


def skip(app, what, name, obj, would_skip, options):  # pylint: disable=unused-argument,too-many-arguments
    """Skip autodoc for __init__ method."""
    if name == "__init__":
        return False
    return would_skip


def setup(app):
    """Setup Sphinx app."""
    app.connect("autodoc-skip-member", skip)
