"""
Utilities for generating an :mod:`argparse` based CLI.
"""
import argparse
import itertools
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)


if TYPE_CHECKING:
    from argparse import FileType

import attrs

import typed_settings as ts

from ._core import _load_settings, default_loaders
from ._dict_utils import _deep_options, _set_path
from .attrs import ARGPARSE_KEY, METADATA_KEY, _SecretRepr
from .cli_utils import StrDict, TypeArgsMaker, TypeHandlerFunc, get_default
from .converters import BaseConverter, default_converter, from_dict
from .loaders import Loader
from .types import ST, SettingsDict


WrapppedFunc = Callable[[ST], Any]


@ts.settings
class Settings:
    x: int = 3
    y: str = ""


CliFn = Callable[[ST], Optional[int]]
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
        if default is not None or is_optional:
            kwargs["default"] = default
        if type and issubclass(type, bool):
            kwargs["action"] = BooleanOptionalAction

        return kwargs

    def handle_collection(
        self,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default: Optional[Collection[Any]],
        is_optional: bool,
    ) -> StrDict:
        kwargs = type_args_maker.get_kwargs(types[0], attrs.NOTHING)
        kwargs["default"] = default
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
            "default": default,
        }
        return kwargs

    def handle_mapping(
        self,
        type_args_maker: TypeArgsMaker,
        types: Tuple[Any, ...],
        default: Any,
        is_optional: bool,
    ) -> StrDict:
        kwargs = {
            "metavar": "KEY=VALUE",
            "multiple": True,
            "action": DictItemAction,
        }
        if isinstance(default, Mapping):
            default = [f"{k}={v}" for k, v in default.items()]
            kwargs["default"] = default
        elif is_optional:
            kwargs["default"] = None

        return kwargs


def cli(
    settings_cls: Type[ST],
    loaders: Union[str, Sequence[Loader]],
    converter: Optional[BaseConverter] = None,
    type_args_maker: Optional[TypeArgsMaker] = None,
    **parser_kwargs: Any,
) -> Callable[[CliFn], DecoratedCliFn]:
    """
    Generate an argument parser for the options of the given settings class
    and pass an instance of it to the decorated function.
    """
    if isinstance(loaders, str):
        loaders = default_loaders(loaders)

    converter = converter or default_converter()
    type_args_maker = type_args_maker or TypeArgsMaker(ArgparseHandler())
    decorator = _get_decorator(
        settings_cls, loaders, converter, type_args_maker, **parser_kwargs
    )
    return decorator


def make_parser(
    settings_cls: Type[ST],
    loaders: Union[str, Sequence[Loader]],
    converter: Optional[BaseConverter] = None,
    type_args_maker: Optional[TypeArgsMaker] = None,
    **parser_kwargs: Any,
) -> argparse.ArgumentParser:
    if isinstance(loaders, str):
        loaders = default_loaders(loaders)
    converter = converter or default_converter()
    type_args_maker = type_args_maker or TypeArgsMaker(ArgparseHandler())

    return _mk_parser(
        settings_cls, loaders, converter, type_args_maker, **parser_kwargs
    )


def namespace2settings(
    settings_cls: Type[ST],
    namespace: argparse.Namespace,
    converter: Optional[BaseConverter] = None,
) -> ST:
    converter = converter or default_converter()
    return _ns2settings(namespace, settings_cls, converter)


def _get_decorator(
    settings_cls: Type[ST],
    loaders: Sequence[Loader],
    converter: BaseConverter,
    type_args_maker: TypeArgsMaker,
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
            if "description" not in parser_kwargs and func.__doc__:
                parser_kwargs["description"] = func.__doc__.strip()
            parser = _mk_parser(
                settings_cls,
                loaders,
                converter,
                type_args_maker,
                **parser_kwargs,
            )

            args = parser.parse_args()
            settings = _ns2settings(args, settings_cls, converter)
            return func(settings)

        return cli_wrapper

    return decorator


def _mk_parser(
    settings_cls: Type[ST],
    loaders: Sequence[Loader],
    converter: BaseConverter,
    type_args_maker: TypeArgsMaker,
    **parser_kwargs: Any,
) -> argparse.ArgumentParser:
    """
    Create an :class:`argparse.ArgumentParser` for all options.
    """
    options = _deep_options(settings_cls)
    settings_dict = _load_settings(settings_cls, options, loaders)
    grouped_options = [
        (g_cls, list(g_opts))
        for g_cls, g_opts in itertools.groupby(options, key=lambda o: o.cls)
    ]
    parser = argparse.ArgumentParser(**parser_kwargs)
    for g_cls, g_opts in grouped_options:
        group = parser.add_argument_group(
            g_cls.__name__, f"{g_cls.__name__} options"
        )
        for oinfo in g_opts:
            default = get_default(
                oinfo.field, oinfo.path, settings_dict, converter
            )
            flags, cfg = _mk_argument(
                oinfo.path, oinfo.field, default, type_args_maker
            )
            group.add_argument(*flags, **cfg)
    return parser


def _mk_argument(
    path: str,
    field: attrs.Attribute,
    default: Any,
    type_args_maker: TypeArgsMaker,
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    user_config = field.metadata.get(METADATA_KEY, {}).get(ARGPARSE_KEY, {})

    # The option type specifies the default option kwargs
    kwargs = type_args_maker.get_kwargs(field.type, default)

    param_decls: Tuple[str, ...]
    user_param_decls: Union[str, Sequence[str]]
    user_param_decls = user_config.pop("param_decls", ())
    if not user_param_decls:
        option_name = path.replace(".", "-").replace("_", "-")
        param_decls = (f"--{option_name}",)
    elif isinstance(user_param_decls, str):
        param_decls = (user_param_decls,)
    else:
        param_decls = tuple(user_param_decls)

    # Get "help" from the user_config *now*, because we may need to update it
    # below.  Also replace "None" with "".
    kwargs["help"] = user_config.pop("help", None) or ""
    if "default" in kwargs and kwargs["default"] is not attrs.NOTHING:
        if kwargs["default"] is None:
            help_extra = ""
        elif isinstance(field.repr, _SecretRepr):
            help_extra = f" [default: {field.repr('')}]"
        else:
            help_extra = f" [default: {kwargs['default']}]"
    else:
        kwargs["required"] = True
        help_extra = " [required]"
    kwargs["help"] = f"{kwargs['help']}{help_extra}"

    # The user has the last word, though.
    kwargs.update(user_config)

    return (param_decls, kwargs)


def _ns2settings(
    namespace: argparse.Namespace,
    settings_cls: Type[ST],
    converter: BaseConverter,
) -> ST:
    """
    Convert the :class:`argparse.Namespace` to an instance of the settings
    class and return it.
    """
    options = _deep_options(settings_cls)
    settings_dict: SettingsDict = {}
    for option_info in options:
        value = getattr(namespace, option_info.path.replace(".", "_"))
        _set_path(settings_dict, option_info.path, value)
    settings = from_dict(settings_dict, settings_cls, converter)
    return settings


class BooleanOptionalAction(argparse.Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        default: Any = None,
        type: Union[Callable[[str], Any], "FileType", None] = None,
        choices: Optional[Iterable[Any]] = None,
        required: bool = False,
        help: Optional[str] = None,
        metavar: Union[str, Tuple[str, ...], None] = None,
    ) -> None:

        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)

            if option_string.startswith("--"):
                option_string = "--no-" + option_string[2:]
                _option_strings.append(option_string)

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

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None,
    ) -> None:
        if option_string in self.option_strings:
            setattr(
                namespace, self.dest, not option_string.startswith("--no-")
            )

    def format_usage(self) -> str:
        return " | ".join(self.option_strings)


class DictItemAction(argparse.Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        nargs: Union[int, str, None] = None,
        default: Any = None,
        type: Union[Callable[[str], Any], "FileType", None] = None,
        choices: Optional[Iterable[Any]] = None,
        required: bool = False,
        help: Optional[str] = None,
        metavar: Union[str, Tuple[str, ...], None] = None,
    ):
        if nargs == 0:
            raise ValueError(
                "nargs for append actions must be != 0; if arg "
                "strings are not supplying the value to append, "
                "the append const action may be more appropriate"
            )
        if const is not None and nargs != argparse.OPTIONAL:
            raise ValueError(
                f"nargs must be {argparse.OPTIONAL!r} to supply const"
            )
        super().__init__(
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

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None,
    ) -> None:
        # def cb(
        #     ctx: click.Context,
        #     param: click.Option,
        #     value: Optional[Iterable[str]],
        # ) -> Optional[Dict[str, str]]:
        #     if not value:
        #         return None if is_optional else {}
        #     splitted = [v.partition("=") for v in value]
        #     items = {k: v for k, _, v in splitted}
        #     return items

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
