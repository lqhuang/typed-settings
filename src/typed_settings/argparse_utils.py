"""
Utilities for generating an :mod:`argparse` based CLI.
"""
import argparse
import itertools
import typing as t
from functools import wraps

import attrs
import cattrs

import typed_settings as ts

from ._core import _load_settings, default_loaders
from ._dict_utils import _deep_options, _set_path
from .converters import default_converter, from_dict
from .loaders import Loader
from .types import OptionInfo, OptionList, SettingsDict, T


WrapppedFunc = t.Callable[[T], t.Any]


@ts.settings
class Settings:
    x: int = 3
    y: str = ""


CliFn = t.Callable[[T], t.Optional[int]]
DecoratedCliFn = t.Callable[[], t.Optional[int]]


def cli(
    cls: t.Type[T],
    loaders: t.Union[str, t.Sequence[Loader]],
    converter: t.Optional[cattrs.Converter] = None,
    # type_handler: "t.Optional[TypeHandler]" = None,
    # argname: t.Optional[str] = None,
    # decorator_factory: "t.Optional[DecoratorFactory]" = None,
    **parser_kwargs: t.Any,
) -> t.Callable[[CliFn], DecoratedCliFn]:
    """
    Generate an argument parser for the options of the given settings class
    and pass an instance of it to the decorated function.
    """
    # Only clean up the users' arguments and let _get_decorator() to the work.
    cls = attrs.resolve_types(cls)
    if isinstance(loaders, str):
        loaders = default_loaders(loaders)
    converter = converter or default_converter()
    decorator = _get_decorator(cls, loaders, converter, **parser_kwargs)
    return decorator


def _get_decorator(
    cls: t.Type[T],
    loaders: t.Sequence[Loader],
    converter: cattrs.Converter,
    **parser_kwargs: t.Any,
) -> t.Callable[[CliFn], DecoratedCliFn]:
    """
    Build the CLI decorator based on the user's config.
    """

    def decorator(func: CliFn) -> DecoratedCliFn:
        """
        Create an argument parsing wrapper for *func*.

        The wrapper

        - loads settings as default option values
        - creates an argument parser with an option for each setting
        - parses the command line options
        - passes the updated settings instance to the decorated function
        """

        @wraps(func)
        def cli_wrapper() -> t.Optional[int]:
            options = _deep_options(cls)
            settings_dict = _load_settings(cls, options, loaders)
            if "description" not in parser_kwargs and func.__doc__:
                parser_kwargs["description"] = func.__doc__.strip()
            parser = _mk_parser(options, settings_dict, **parser_kwargs)

            args = parser.parse_args()
            settings = _ns2settings(args, cls, options, converter)
            return func(settings)

        return cli_wrapper

    return decorator


def _mk_parser(
    options: OptionList,
    settings_dict: SettingsDict,
    **parser_kwargs: t.Any,
) -> argparse.ArgumentParser:
    """
    Create an :class:`argparse.ArgumentParser` for all options.
    """
    grouped_options = [
        (g_cls, list(g_opts))
        for g_cls, g_opts in itertools.groupby(options, key=lambda o: o.cls)
    ]
    parser = argparse.ArgumentParser(**parser_kwargs)
    parser.add_argument(
        "--x",
        type=int,
        default=0,
        help="an integer for the accumulator",
    )
    parser.add_argument(
        "--y",
        default="",
        # dest="accumulate",
        # action="store_const",
        # const=sum,
        # default=max,
        # help="sum the integers (default: find the max)",
    )
    return parser


def _ns2settings(
    namespace: argparse.Namespace,
    settings_cls: t.Type[T],
    options: t.List[OptionInfo],
    converter: cattrs.Converter,
) -> T:
    """
    Convert the :class:`argparse.Namespace` to an instance of the settings
    class and return it.
    """
    settings_dict: SettingsDict = {}
    for option_info in options:
        value = getattr(namespace, option_info.path.replace(".", "_"))
        _set_path(settings_dict, option_info.path, value)
    settings = from_dict(settings_dict, settings_cls, converter)
    return settings


@cli(Settings, "myapp")
def main(settings: Settings) -> None:
    """
    My cli

    Spam eggs
    """
    print(settings)


if __name__ == "__main__":
    main()
