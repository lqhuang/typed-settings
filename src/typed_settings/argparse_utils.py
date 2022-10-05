"""
Utilities for generating an :mod:`argparse` based CLI.
"""
import argparse
import itertools
from functools import wraps
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

import attrs
import cattrs

import typed_settings as ts

from ._core import _load_settings, default_loaders
from ._dict_utils import _deep_options, _set_path
from .cli_utils import StrDict, TypeArgsMaker, TypeHandlerFunc
from .converters import default_converter, from_dict
from .loaders import Loader
from .types import OptionInfo, OptionList, SettingsDict, T


WrapppedFunc = Callable[[T], Any]


@ts.settings
class Settings:
    x: int = 3
    y: str = ""


CliFn = Callable[[T], Optional[int]]
DecoratedCliFn = Callable[[], Optional[int]]

#: Default handlers for click option types.
DEFAULT_TYPES: Dict[type, TypeHandlerFunc] = {
    # datetime: handle_datetime,
    # Enum: handle_enum,
}


class ArgparseHandler:
    def __init__(
        self, extra_types: Optional[Dict[type, TypeHandlerFunc]] = None
    ) -> None:
        self.extra_types = extra_types or DEFAULT_TYPES

    def get_scalar_handlers(self) -> Dict[type, TypeHandlerFunc]:
        return self.extra_types

    def handle_scalar(
        self,
        type: Optional[type],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        kwargs: StrDict = {"type": type}
        if default is not attrs.NOTHING:
            kwargs["default"] = default
        if type and issubclass(type, bool):
            kwargs["action"] = argparse.BooleanOptionalAction

        return kwargs

    def handle_collection(
        self,
        # kwargs: StrDict,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default: Optional[Collection[Any]],
        is_optional: bool,
    ) -> StrDict:
        kwargs = type_args_maker.get_kwargs(types[0], attrs.NOTHING)

        if isinstance(default, Collection):
            # Call get_kwargs() to get proper default value formatting
            default = [
                type_args_maker.get_kwargs(types[0], d)["default"]
                for d in default
            ]
        else:
            default = None

        if isinstance(default, Collection):
            kwargs["default"] = default
        elif is_optional:
            kwargs["default"] = None
        kwargs["action"] = "append"

        return kwargs

    def handle_tuple(
        self,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        kwargs = {
            "type": types,
            "nargs": len(types),
        }
        if isinstance(default, tuple):
            kwargs["default"] = tuple(
                type_args_maker.get_kwargs(t, d)["default"]
                for t, d in zip(types, default)
            )
        elif is_optional:
            kwargs["default"] = None

        # {type, default, nargs} => {type, default, nargs}

        return kwargs

    def handle_mapping(
        self,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default,
        is_optional,
    ) -> StrDict:
        def cb(
            ctx: click.Context,
            param: click.Option,
            value: Optional[Iterable[str]],
        ) -> Optional[Dict[str, str]]:
            if not value:
                return None if is_optional else {}
            splitted = [v.partition("=") for v in value]
            items = {k: v for k, _, v in splitted}
            return items

        kwargs = {
            "metavar": "KEY=VALUE",
            "multiple": True,
            "callback": cb,
        }
        if isinstance(default, Mapping):
            default = [f"{k}={v}" for k, v in default.items()]
            kwargs["default"] = default
        elif is_optional:
            kwargs["default"] = None

        # {metavar, default, multiple, callback} => {metavar, default, }

        return kwargs


def cli(
    cls: Type[T],
    loaders: Union[str, Sequence[Loader]],
    converter: Optional[cattrs.Converter] = None,
    # type_handler: "Optional[TypeHandler]" = None,
    # argname: Optional[str] = None,
    # decorator_factory: "Optional[DecoratorFactory]" = None,
    **parser_kwargs: Any,
) -> Callable[[CliFn], DecoratedCliFn]:
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
    cls: Type[T],
    loaders: Sequence[Loader],
    converter: cattrs.Converter,
    **parser_kwargs: Any,
) -> Callable[[CliFn], DecoratedCliFn]:
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
        def cli_wrapper() -> Optional[int]:
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
    **parser_kwargs: Any,
) -> argparse.ArgumentParser:
    """
    Create an :class:`argparse.ArgumentParser` for all options.
    """
    grouped_options = [
        (g_cls, list(g_opts))
        for g_cls, g_opts in itertools.groupby(options, key=lambda o: o.cls)
    ]
    parser = argparse.ArgumentParser(**parser_kwargs)
    for g_cls, g_opts in grouped_options:
        group = parser.add_group(g_cls.__name__, f"{g_cls.__name} options")
        for oinfo in g_opts:
            flags, cfg = _mk_argument(
                oinfo.path, oinfo.field, default, type_handler
            )
            group.add_argument(*flags, **cfg)
    return parser


def _mk_argument(
    path: str,
    field: attrs.Attribute,
    default: Any,
    type_handler: "TypeHandler",
) -> Tuple[List[str], Dict[str, Any]]:
    # add_argument(
    #     name or flags...,
    #     action,
    #     nargs,
    #     const,
    #     default,
    #     type,
    #     choices,
    #     required,
    #     help,
    #     metavar,
    #     dest,
    # )
    argparse.BooleanOptionalAction
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


def _ns2settings(
    namespace: argparse.Namespace,
    settings_cls: Type[T],
    options: List[OptionInfo],
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


class BooleanOptionalAction(argparse.Action):
    def __init__(
        self,
        option_strings,
        dest,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
    ):

        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)

            if option_string.startswith("--"):
                option_string = "--no-" + option_string[2:]
                _option_strings.append(option_string)

        if (
            help is not None
            and default is not None
            and default is not SUPPRESS
        ):
            help += " (default: %(default)s)"

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=0,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string in self.option_strings:
            setattr(
                namespace, self.dest, not option_string.startswith("--no-")
            )

    def format_usage(self):
        return " | ".join(self.option_strings)


class DictItemAction(argparse.Action):
    def __init__(
        self,
        option_strings,
        dest,
        nargs=None,
        const=None,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
    ):
        if nargs == 0:
            raise ValueError(
                "nargs for append actions must be != 0; if arg "
                "strings are not supplying the value to append, "
                "the append const action may be more appropriate"
            )
        if const is not None and nargs != OPTIONAL:
            raise ValueError("nargs must be %r to supply const" % OPTIONAL)
        super(_AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = dict(items)
        items.append(values)
        setattr(namespace, self.dest, items)


@cli(Settings, "myapp")
def main(settings: Settings) -> None:
    """
    My cli

    Spam eggs
    """
    print(settings)


if __name__ == "__main__":
    main()
