"""
Configuration for Sphinx docs.
"""
from importlib.metadata import version as get_version


project = "Typed Settings"
author = "Stefan Scherfke"
copyright = "2020, Stefan Scherfke"
release = get_version("typed-settings")
version = ".".join(release.split(".")[0:2])


extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "smartquotes",
]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


html_theme = "furo"
html_theme_options = {
    # "logo_only": True,
    # "sidebar_hide_name": True,
    "light_css_variables": {
        "color-brand-primary": "#266DB4",
        "color-brand-content": "#266DB4",
    },
    "dark_css_variables": {
        "color-brand-primary": "#3186DC",
        "color-brand-content": "#3186DC",
    },
}
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]
html_logo = "_static/typed-settings-spacing.svg"
html_title = "Typed Settings"


# Autodoc
autodoc_member_order = "bysource"

# Copybutton
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "attrs": ("https://www.attrs.org/en/stable/", None),
    "cattrs": ("https://catt.rs/en/latest/", None),
    "click": ("https://click.palletsprojects.com/en/latest/", None),
    "click-option-group": (
        "https://click-option-group.readthedocs.io/en/latest/",
        None,
    ),
}


# Workaround for https://github.com/sphinx-doc/sphinx/issues/10785
# (Type aliases are not properly resolved, change "py:class" to "py:data")
TYPE_ALIASES = ["SettingsDict"]


def resolve_type_aliases(app, env, node, contnode):
    """Resolve :class: references to our type aliases as :attr: instead."""
    if (
        node["refdomain"] == "py"
        and node["reftype"] == "class"
        and node["reftarget"] in TYPE_ALIASES
    ):
        return app.env.get_domain("py").resolve_xref(
            env, node["refdoc"], app.builder, "data", node["reftarget"], node, contnode
        )


def setup(app):  # noqa: D103
    app.connect("missing-reference", resolve_type_aliases)
