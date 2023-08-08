"""
This module contains the settings processors provided by Typed Settings and the
protocol specification that they must implement.
"""
import logging
import subprocess
from typing import Any, Dict, Protocol

from .dict_utils import iter_settings, set_path
from .types import OptionList, SettingsClass, SettingsDict


__all__ = [
    "Protocol",
    "UrlHandler",
    "Processor",
    "UrlProcessor",
    "handle_raw",
    "handle_script",
    "handle_op",
    "FormatProcessor",
    "JinjaProcessor",
]


LOGGER = logging.getLogger("typed_settings")


class Processor(Protocol):
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

        You may modify settings_dict in place - you don't need to return a
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

    .. versionadded:: 23.0.0
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

        You may modify settings_dict in place - you don't need to return a
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

    .. versionadded:: 23.0.0
    """
    return value


def handle_script(value: str, scheme: str) -> str:
    """
    **URL handler:** Run *value* as shell script and return its output.

    .. versionadded:: 23.0.0
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

    .. versionadded:: 23.0.0
    """
    from . import _onepassword

    return _onepassword.get_resource(f"op://{value}")


class FormatProcessor:
    """
    Perform value interpolation / templating via Python format strings.

    Formatting is performed recursively as long as the value is a valid format
    string.

    No exceptions are raised.  If format strings are invalid or refer to
    non existing values, they are returned unchanged.

    .. versionadded:: 23.0.0
    """

    def __call__(
        self,
        settings_dict: SettingsDict,
        settings_cls: SettingsClass,
        options: OptionList,
    ) -> SettingsDict:
        """
        Invoke the processor to render all values in the settings dict.
        """
        for path, value in iter_settings(settings_dict, options):
            value = self._render(value, settings_dict)
            set_path(settings_dict, path, value)

        return settings_dict

    def _render(self, value: Any, settings_dict: SettingsDict) -> Any:
        """
        Recursively render *value*.
        """
        if not self._is_possibly_format_string(value):
            return value

        try:
            new_value = value.format(**settings_dict)
        except Exception:
            return value

        if new_value == value:
            return new_value

        value = self._render(new_value, settings_dict)
        return value

    def _is_possibly_format_string(self, value: Any) -> bool:
        """
        Guess if *value* may be format string.

        It only detectecs if *value* is certainly *not* a format string and
        returns ``False`` in that case.
        If it returns ``True``, it may or may not be a valid format string.
        """
        return isinstance(value, str) and "{" in value and "}" in value


class JinjaProcessor:
    """
    Perform value templating with Jinja__.

    __ https://palletsprojects.com/p/jinja/

    Rendering is performed recursively as long as the value is a valid Jinja
    template.

    No exceptions are raised.  If templates are invalid or refer to non
    existing values, they are returned unchanged.

    Raises:
        ModuleNotFoundError: If ``jinja2`` is not installed.

    .. versionadded:: 23.0.0
    """

    def __init__(self) -> None:
        try:
            import jinja2
        except ImportError as e:
            raise ModuleNotFoundError(
                "Module 'jinja2' not installed.  Please run "
                "'python -m pip install -U typed-settings[jinja]'"
            ) from e

        self._jinja2 = jinja2
        # autoescape msut be False or recursive rendering will not work
        # properly.
        self._env = jinja2.Environment(autoescape=False)  # noqa: S701

    def __call__(
        self,
        settings_dict: SettingsDict,
        settings_cls: SettingsClass,
        options: OptionList,
    ) -> SettingsDict:
        """
        Invoke the processor to render all values in the settings dict.
        """
        for path, value in iter_settings(settings_dict, options):
            value = self.render(value, settings_dict)
            set_path(settings_dict, path, value)

        return settings_dict

    def render(self, value: Any, settings_dict: SettingsDict) -> Any:
        """
        Recursively render *value*.
        """
        if not self.is_possibly_template(value):
            return value

        try:
            template = self._env.from_string(value)
            value = template.render(**settings_dict)
        except self._jinja2.TemplateError:
            return value

        value = self.render(value, settings_dict)
        return value

    def is_possibly_template(self, value: Any) -> bool:
        """
        Guess if *value* may be format string.

        It only detectecs if *value* is certainly *not* a format string and
        returns ``False`` in that case.
        If it returns ``True``, it may or may not be a valid format string.
        """
        if isinstance(value, str):
            for marker in (
                self._env.block_start_string,
                self._env.variable_start_string,
                self._env.comment_start_string,
            ):
                if marker in value:
                    return True
        return False
