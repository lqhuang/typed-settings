"""
Exceptions raised by Typed Settings.
"""


class TsError(Exception):
    """
    **Basse class** for all typed settings exceptions.
    """


class UnknownFormatError(TsError):
    """
    Raised when no file format loader is configured for a given config file.
    """


class ConfigFileNotFoundError(TsError):
    """
    Raised when a mandatory config file does not exist.
    """


class ConfigFileLoadError(TsError):
    """
    Raised when a config file exists but cannot be read or parsed/loaded.
    """


class InvalidOptionsError(TsError):
    """
    Raised when loaded settings contain an option that is not defined in the
    settings class.
    """


class InvalidValueError(TsError):
    """
    Raised the value of an option cannot be converted to the correct type.
    """
