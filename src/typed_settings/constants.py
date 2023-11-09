"""
Global constants shared by different modules.

.. versionadded: 23.1.1
"""
from typing import Final


#: Representation for redacted secrets
SECRET_REPR: Final[str] = "*******"

#: Key used in the field metadata
METADATA_KEY: Final[str] = "typed-settings"

#: Key for argparse option within Typed Settings' metadata
ARGPARSE_METADATA_KEY: Final[str] = "argparse"

#: Key for click option within Typed Settings' metadata
CLICK_METADATA_KEY: Final[str] = "click"
