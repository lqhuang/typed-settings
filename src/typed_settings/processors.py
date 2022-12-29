"""
This module contains the settings processors provided by Typed Settings and the
protocol specification that they must implement.
"""
import logging
import subprocess  # noqa: S404
from typing import Dict

from ._compat import Protocol
from .dict_utils import iter_settings, set_path
from .types import OptionList, SettingsClass, SettingsDict


LOGGER = logging.getLogger("typed_settings")


class Processors(Protocol):
    """
    **Protocol** that settings processors must implement.

    Processors must be callables (e.g., functions) with the specified
    signature.

    .. versionadded:: 23.0.0
    """

    def __call__(
        self,
        settings_dict: SettingsDict,
        settings_cls: SettingsClass,
        options: OptionList,
    ) -> SettingsDict:
        """
        Modify or update values in *settings_dict* and return an updated
        version.

        You may modify settings_dict in place – you don't need to return a
        copy of it.

        You should not add additional keys.

        Args:
            settings_dict: The dict of loaded settings.  Values are not yet
                converted to the target type (e.g., ``int`` values loaded from
                an env var are still a string).
            settings_cls: The base settings class for all options.
            options: The list of available settings.

        Return:
            The updated settings dict.
        """
        ...


class UrlHandler(Protocol):
    """
    **Protocol** that handlers for :class:`UrlProcessor` must implement.

    Handlers must be callables (e.g., functions) with the specified signature.

    .. versionadded:: 23.0.0
    """

    def __call__(self, value: str, scheme: str) -> str:
        """
        Handle the URL resource *value* and return the result.

        Args:
            value: The URL without the scheme (the ``v`` in ``s://v``).
            scheme: The URL scheme (the ``s://` in ``s://v``).

        Return:
            The result of the operation.

        Raise:
            ValueError: If the URL is invalid or another error occurs while
                handling the URL.
        """
        ...


class UrlProcessor:
    """
    Modify values that match one of the configured URL schemes.

    Args:
        handlers: A dictionary mapping URL schemes to handler functions.
    """

    def __init__(self, handlers: Dict[str, UrlHandler]) -> None:
        self.handlers = handlers
        """
        Registered URL scheme handlers.

        You can modify this dict after an instance of this class has been
        created.
        """

    def __call__(
        self,
        settings_dict: SettingsDict,
        settings_cls: SettingsClass,
        options: OptionList,
    ) -> SettingsDict:
        """
        Modify or update values in *settings_dict* and return an updated
        version.

        You may modify settings_dict in place – you don't need to return a
        copy of it.

        You should not add additional keys.

        Args:
            settings_dict: The dict of loaded settings.  Values are not yet
                converted to the target type (e.g., ``int`` values loaded from
                an env var are still a string).
            settings_cls: The base settings class for all options.
            options: The list of available settings.

        Return:
            The updated settings dict.
        """
        for path, value in iter_settings(settings_dict, options):
            for scheme, handler in self.handlers.items():
                if isinstance(value, str) and value.startswith(scheme):
                    start_idx = len(scheme)
                    value = value[start_idx:]
                    value = handler(value, scheme)
                    set_path(settings_dict, path, value)
                    break  # Only process a value once!

        return settings_dict


def handle_raw(value: str, scheme: str) -> str:
    """
    **URL handler:** Return *value* unchanged.
    """
    return value


def handle_script(value: str, scheme: str) -> str:
    """
    **URL handler:** Run *value* as shell script and return its output.
    """
    try:
        result = subprocess.run(
            value,
            shell=True,  # noqa: S602
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        msg = (
            f"Helper script failed: {scheme}{value}\n"
            f"EXIT CODE: {e.returncode}\n"
            f"STDOUT:\n{e.stdout}"
            f"STDERR:\n{e.stderr}"
        )
        raise ValueError(msg) from e


def handle_op(value: str, scheme: str) -> str:
    """
    **URL handler:** Retrieve the resource *value* from the `1Password CLI`_.

    You must must have installed it and set it up in order for this to work.

    .. _1Password CLI: https://developer.1password.com/docs/cli/
    """
    from . import onepassword

    return onepassword.get_resource(f"op://{value}")
