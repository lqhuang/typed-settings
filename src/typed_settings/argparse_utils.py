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
from .types import OptionInfo, SettingsDict, T


WrapppedFunc = t.Callable[[T], t.Any]


@ts.settings
class Settings:
    x: int = 3
    y: str = ""


CliFn = t.Callable[[T], t.Optional[int]]
DecoratedCliFn = t.Callable[[], t.Optional[int]]


def mkcli(
    cls: t.Type[T],
    loaders: t.Union[str, t.Sequence[Loader]],
    converter: t.Optional[cattrs.Converter] = None,
    # type_handler: "t.Optional[TypeHandler]" = None,
    # argname: t.Optional[str] = None,
    # decorator_factory: "t.Optional[DecoratorFactory]" = None,
    **parser_kwargs: t.Any,
) -> t.Callable[[CliFn], DecoratedCliFn]:
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
    options = _deep_options(cls)
    grouped_options = [
        (g_cls, list(g_opts))
        for g_cls, g_opts in itertools.groupby(options, key=lambda o: o.cls)
    ]

    def decorator(func: CliFn) -> DecoratedCliFn:
        if "description" not in parser_kwargs:
            try:
                docstr = func.__doc__.strip().splitlines()[0]  # type: ignore
                parser_kwargs["description"] = docstr
            except (AttributeError, IndexError):
                pass

        settings_dict = _load_settings(cls, options, loaders)
        parser = _mk_parser(grouped_options, settings_dict, **parser_kwargs)

        @wraps(func)
        def cli_wrapper() -> t.Optional[int]:
            args = parser.parse_args()
            settings = _ns2settings(args, cls, options, converter)
            return func(settings)

        return cli_wrapper

    return decorator


def _mk_parser(
    grouped_options: t.List[t.Tuple[type, t.List[OptionInfo]]],
    settings_dict: SettingsDict,
    **parser_kwargs: t.Any,
) -> argparse.ArgumentParser:
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
    settings_dict: SettingsDict = {}
    for option_info in options:
        value = getattr(namespace, option_info.path.replace(".", "_"))
        _set_path(settings_dict, option_info.path, value)
    settings = from_dict(settings_dict, settings_cls, converter)
    return settings


@mkcli(Settings, "myapp")
def cli(settings: Settings) -> None:
    """
    My cli
    """
    print(settings)


if __name__ == "__main__":
    cli()
