from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
)
from typing import Any, Dict, List, Optional, Tuple, Union

import attrs
import pytest

from typed_settings import cli_utils, default_converter
from typed_settings._compat import PY_39, PY_310, get_args, get_origin


def handle_int(
    type: type, default: cli_utils.Default, is_optional: bool
) -> cli_utils.StrDict:
    return {
        "type": type,
        "default": default,
        "is_optional": is_optional,
        "called": "special",
    }


class TypeHandler:
    def get_scalar_handlers(self) -> Dict[type, cli_utils.TypeHandlerFunc]:
        return {
            int: handle_int,
        }

    def handle_scalar(
        self,
        type: Optional[type],
        default: cli_utils.Default,
        is_optional: bool,
    ) -> cli_utils.StrDict:
        return {
            "type": type,
            "default": default,
            "is_optional": is_optional,
            "called": "scalar",
        }

    def handle_tuple(
        self,
        type_args_maker: cli_utils.TypeArgsMaker,
        args: Tuple[Any, ...],
        default: Optional[Tuple],
        is_optional: bool,
    ) -> cli_utils.StrDict:
        return {
            "type_args_maker": type_args_maker,
            "args": args,
            "default": default,
            "is_optional": is_optional,
            "called": "tuple",
        }

    def handle_collection(
        self,
        type_args_maker: cli_utils.TypeArgsMaker,
        args: Tuple[Any, ...],
        default: Optional[List[Any]],
        is_optional: bool,
    ) -> cli_utils.StrDict:
        return {
            "type_args_maker": type_args_maker,
            "args": args,
            "default": default,
            "is_optional": is_optional,
            "called": "collection",
        }

    def handle_mapping(
        self,
        type_args_maker: cli_utils.TypeArgsMaker,
        args: Tuple[Any, ...],
        default: cli_utils.Default,
        is_optional: bool,
    ) -> cli_utils.StrDict:
        return {
            "type_args_maker": type_args_maker,
            "args": args,
            "default": default,
            "is_optional": is_optional,
            "called": "mapping",
        }


class TestTypeArgsMaker:
    @pytest.fixture
    def tam(self) -> cli_utils.TypeArgsMaker:
        return cli_utils.TypeArgsMaker(TypeHandler())

    @pytest.mark.parametrize("default", [3, None, attrs.NOTHING])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_special(
        self,
        default: cli_utils.Default,
        is_optional: bool,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM calls calls "TypeHandler.get_scalar_handlers()", then the correct
        handler and returns its results.
        """
        t = Optional[int] if is_optional else int
        result = tam.get_kwargs(t, default)
        assert result == {
            "type": int,
            "default": None if is_optional and not default else default,
            "is_optional": is_optional,
            "called": "special",
        }

    @pytest.mark.parametrize("default", ["x", None, attrs.NOTHING])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_scalar(
        self,
        default: cli_utils.Default,
        is_optional: bool,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM calls calls "TypeHandler.handle_scalar()" and returns its results.
        """
        t = Optional[str] if is_optional else str
        result = tam.get_kwargs(t, default)
        assert result == {
            "type": str,
            "default": None if is_optional and not default else default,
            "is_optional": is_optional,
            "called": "scalar",
        }

    @pytest.mark.parametrize("default", [(1, "x"), None, attrs.NOTHING])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_tuple(
        self,
        default: cli_utils.Default,
        is_optional: bool,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM calls calls "TypeHandler.handle_tuple()" and returns its results.
        """
        t = Optional[Tuple[int, str]] if is_optional else Tuple[int, str]
        result = tam.get_kwargs(t, default)
        assert result == {
            "type_args_maker": tam,
            "args": (int, str),
            "default": default or None,
            "is_optional": is_optional,
            "called": "tuple",
        }

    def test_tuple_wrong_deault_len(
        self,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM raises an error if a tuple default has the wrong length.
        """
        with pytest.raises(
            TypeError, match="Default value must be of len 2: 3"
        ):
            tam.get_kwargs(Tuple[int, str], (1, "x", True))

    @pytest.mark.skipif(not PY_39, reason="Needs Python 3.8")
    @pytest.mark.parametrize("default", [[1, 2], None, attrs.NOTHING])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_listtuple(
        self,
        default: cli_utils.Default,
        is_optional: bool,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM calls calls "TypeHandler.handle_collection()" for list-like tuples
        and returns its results.
        """
        t = Optional[tuple[int, ...]] if is_optional else tuple[int, ...]
        result = tam.get_kwargs(t, default)
        assert result == {
            "type_args_maker": tam,
            "args": (int, ...),
            "default": default or None,
            "is_optional": is_optional,
            "called": "collection",
        }

    @pytest.mark.skipif(not PY_39, reason="Needs Python 3.8")
    @pytest.mark.parametrize(
        "ctype", [list, Sequence, MutableSequence, set, frozenset, MutableSet]
    )
    @pytest.mark.parametrize("default", [[1, 2], None, attrs.NOTHING])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_collection(
        self,
        ctype: Any,
        default: cli_utils.Default,
        is_optional: bool,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM calls calls "TypeHandler.handle_collection()" and returns its
        results.
        """
        t = Optional[ctype[int]] if is_optional else ctype[int]
        result = tam.get_kwargs(t, default)
        assert result == {
            "type_args_maker": tam,
            "args": (int,),
            "default": default or None,
            "is_optional": is_optional,
            "called": "collection",
        }

    @pytest.mark.skipif(not PY_39, reason="Needs Python 3.8")
    @pytest.mark.parametrize("ctype", [dict, Mapping, MutableMapping])
    @pytest.mark.parametrize("default", [{"a": 1}, None, attrs.NOTHING])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_mapping(
        self,
        ctype: Any,
        default: cli_utils.Default,
        is_optional: bool,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM calls calls "TypeHandler.handle_mapping()" and returns its results.
        """
        t = Optional[ctype[str, int]] if is_optional else ctype[str, int]
        result = tam.get_kwargs(t, default)
        assert result == {
            "type_args_maker": tam,
            "args": (str, int),
            "default": None if is_optional and not default else default,
            "is_optional": is_optional,
            "called": "mapping",
        }

    @pytest.mark.parametrize("default", ["x", None, attrs.NOTHING])
    def test_none(
        self,
        default: cli_utils.Default,
        tam: cli_utils.TypeArgsMaker,
    ) -> None:
        """
        TAM calls calls "TypeHandler.handle_scalar()" and returns its results.
        """
        result = tam.get_kwargs(None, default)
        assert result == {
            "type": None,
            "default": default,
            "is_optional": False,
            "called": "scalar",
        }

    def test_unsupported(self, tam: cli_utils.TypeArgsMaker) -> None:
        """
        TAM raises a TypeError if it encounters an unsupported type.
        """
        with pytest.raises(TypeError, match="Cannot create CLI option for"):
            tam.get_kwargs(Union[int, str], 3)


@pytest.mark.parametrize(
    "default, path, type, settings, expected",
    [
        (attrs.NOTHING, "a", int, {"a": 3}, 3),
        (attrs.NOTHING, "a", int, {}, attrs.NOTHING),
        (2, "a", int, {}, 2),
        (attrs.Factory(list), "a", List[int], {}, []),
        (attrs.NOTHING, "a", None, {"a": "3"}, "3"),
    ],
)
def test_get_default(
    default: object,
    path: str,
    type: type,
    settings: dict,
    expected: object,
) -> None:
    """
    "get_default()" returns the loaded setting if possible or else the field's
    default value.
    """
    converter = default_converter()
    field = attrs.Attribute(  # type: ignore[call-arg,var-annotated]
        "test", default, None, None, None, None, None, None, type=type
    )
    result = cli_utils.get_default(field, path, settings, converter)
    assert result == expected


def test_get_default_factory() -> None:
    """
    If the factory "takes self", ``None`` is passed since we do not yet have an
    instance.
    """

    def factory(self) -> str:
        assert self is None
        return "eggs"

    default = attrs.Factory(factory, takes_self=True)
    field = attrs.Attribute(  # type: ignore[call-arg,var-annotated]
        "test", default, None, None, None, None, None, None, type=str
    )
    result = cli_utils.get_default(field, "a", {}, default_converter())
    assert result == "eggs"


def test_get_default_cattrs_error() -> None:
    """
    "get_default()" checks if cattrs can convert a loaded default.
    """
    converter = default_converter()
    field = attrs.Attribute(  # type: ignore[call-arg,var-annotated]
        "test",
        attrs.NOTHING,
        None,
        None,
        None,
        None,
        None,
        None,
        type=List[int],
    )
    with pytest.raises(ValueError, match="Invalid default for type"):
        cli_utils.get_default(field, "a", {"a": ["spam"]}, converter)


OPTIONAL_TEST_DATA = [
    (int, 3, (int, 3, None, (), False)),
    (int, attrs.NOTHING, (int, attrs.NOTHING, None, (), False)),
    (Optional[int], 3, (int, 3, None, (), True)),
    (Optional[int], None, (int, None, None, (), True)),
    (Optional[int], attrs.NOTHING, (int, None, None, (), True)),
    (Union[int, None], 3, (int, 3, None, (), True)),
    (Union[int, None], None, (int, None, None, (), True)),
    (Union[int, None], attrs.NOTHING, (int, None, None, (), True)),
    (Union[None, int], 3, (int, 3, None, (), True)),
    (Union[None, int], None, (int, None, None, (), True)),
    (Union[None, int], attrs.NOTHING, (int, None, None, (), True)),
    (List[int], None, (List[int], None, list, (int,), False)),
    (Optional[List[int]], None, (List[int], None, list, (int,), True)),
    (None, None, (None, None, None, (), False)),
]
if PY_310:
    OPTIONAL_TEST_DATA += [  # type: ignore[misc]  # type: ignore[misc]
        (int | None, 3, (int, 3, None, (), True)),
        (int | None, None, (int, None, None, (), True)),
        (int | None, attrs.NOTHING, (int, None, None, (), True)),
    ]


@pytest.mark.parametrize("t, d, expected", OPTIONAL_TEST_DATA)
def test_is_optional(
    t: Optional[type],
    d: Any,
    expected: Tuple[Optional[type], Any, Any, Tuple[Any, ...], bool],
) -> None:
    """
    Check if optional detects "Optional[T]", Union[T, None], and "T | None".
    """
    result = cli_utils.check_if_optional(t, d, get_origin(t), get_args(t))
    assert result == expected
