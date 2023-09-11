"""
Tests for "typed_settings.cli_utils".
"""
from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    get_args,
    get_origin,
)

import attrs
import pytest

from typed_settings import cli_utils, default_converter, types
from typed_settings._compat import PY_39, PY_310


def test_nodefaulttype_singleton() -> None:
    """
    `NoDefaultType()`  is a singleton.
    """
    assert cli_utils.NoDefaultType() is cli_utils.NO_DEFAULT


def test_nodefaulttype_repr() -> None:
    """
    `NoDefaultType()` has a nice repr.
    """
    assert repr(cli_utils.NoDefaultType()) == "NO_DEFAULT"


def _none_or_default(default: Any, is_optional: bool) -> Any:
    """
    Return "None" for "NO_DEFAULT" for optional options.
    """
    if is_optional and (default is None or default is cli_utils.NO_DEFAULT):
        return None
    return default


def handle_int(type: type, default: Any, is_optional: bool) -> cli_utils.StrDict:
    """
    An example handler function for the test TypeHandler.
    """
    return {
        "type": type,
        "default": default,
        "is_optional": is_optional,
        "called": "special",
    }


class TypeHandler:
    """
    An example TypeHandler for testing.
    """

    def get_scalar_handlers(self) -> Dict[type, cli_utils.TypeHandlerFunc]:
        return {
            int: handle_int,
        }

    def handle_scalar(
        self,
        type: Optional[type],
        default: Any,
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
        default: Any,
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
    """
    Tests for "TypeArgsMaker".
    """

    @pytest.fixture
    def tam(self) -> cli_utils.TypeArgsMaker:
        return cli_utils.TypeArgsMaker(TypeHandler())

    @pytest.mark.parametrize("default", [3, None, cli_utils.NO_DEFAULT])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_special(
        self,
        default: Any,
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
            "default": _none_or_default(default, is_optional),
            "is_optional": is_optional,
            "called": "special",
        }

    @pytest.mark.parametrize("default", ["x", None, cli_utils.NO_DEFAULT])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_scalar(
        self,
        default: Any,
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
            "default": _none_or_default(default, is_optional),
            "is_optional": is_optional,
            "called": "scalar",
        }

    @pytest.mark.parametrize("default", [(1, "x"), None, cli_utils.NO_DEFAULT])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_tuple(
        self,
        default: Any,
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
            "default": _none_or_default(default, is_optional=True),
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
        with pytest.raises(TypeError, match="Default value must be of len 2: 3"):
            tam.get_kwargs(Tuple[int, str], (1, "x", True))

    @pytest.mark.skipif(not PY_39, reason="Needs Python 3.8")
    @pytest.mark.parametrize("default", [[1, 2], None, cli_utils.NO_DEFAULT])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_listtuple(
        self,
        default: Any,
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
            "default": _none_or_default(default, is_optional=True),
            "is_optional": is_optional,
            "called": "collection",
        }

    @pytest.mark.skipif(not PY_39, reason="Needs Python 3.8")
    @pytest.mark.parametrize(
        "ctype", [list, Sequence, MutableSequence, set, frozenset, MutableSet]
    )
    @pytest.mark.parametrize("default", [[1, 2], None, cli_utils.NO_DEFAULT])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_collection(
        self,
        ctype: Any,
        default: Any,
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
            "default": _none_or_default(default, is_optional=True),
            "is_optional": is_optional,
            "called": "collection",
        }

    @pytest.mark.skipif(not PY_39, reason="Needs Python 3.8")
    @pytest.mark.parametrize("ctype", [dict, Mapping, MutableMapping])
    @pytest.mark.parametrize("default", [{"a": 1}, None, cli_utils.NO_DEFAULT])
    @pytest.mark.parametrize("is_optional", [True, False])
    def test_mapping(
        self,
        ctype: Any,
        default: Any,
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
            "default": _none_or_default(default, is_optional),
            "is_optional": is_optional,
            "called": "mapping",
        }

    @pytest.mark.parametrize("default", ["x", None, cli_utils.NO_DEFAULT])
    def test_none(
        self,
        default: Any,
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
    "name, cls, default, settings, expected",
    [
        (
            "a",
            int,
            attrs.NOTHING,
            {"a": types.LoadedValue(3, types.LoaderMeta("Dummy"))},
            3,
        ),
        ("a", int, attrs.NOTHING, {}, cli_utils.NO_DEFAULT),
        ("a", int, 2, {}, 2),
        ("a", List[int], attrs.Factory(list), {}, None),
        (
            "a",
            None,
            attrs.NOTHING,
            {"a": types.LoadedValue("3", types.LoaderMeta("Dummy"))},
            "3",
        ),
    ],
)
def test_get_default(
    name: str,
    cls: type,
    default: object,
    settings: dict,
    expected: object,
) -> None:
    """
    "get_default()" returns the loaded setting if possible or else the field's
    default value.
    """
    converter = default_converter()
    oinfo = types.OptionInfo(
        parent_cls=type,
        path=name,
        cls=cls,
        default=default,
        has_no_default=default is attrs.NOTHING,
        default_is_factory=isinstance(default, cast(type, attrs.Factory)),
    )
    result = cli_utils.get_default(oinfo, settings, converter)
    if isinstance(default, attrs.Factory):  # type: ignore[arg-type]
        assert callable(result)
        assert result.__name__ == cli_utils.DEFAULT_SENTINEL_NAME
        assert result() is expected
    else:
        assert result == expected


def test_get_default_factory() -> None:
    """
    Default factories are not invoked to generate a default value.
    """

    def factory(self: None) -> str:
        pytest.fail("This should not be invoked")

    default = attrs.Factory(factory, takes_self=True)
    attrs.Attribute(  # type: ignore[call-arg,var-annotated]
        "test", default, None, None, None, None, None, None, type=str
    )
    oinfo = types.OptionInfo(
        parent_cls=type,
        path="a",
        cls=str,
        default=default,
        has_no_default=False,
        default_is_factory=True,
    )
    result = cli_utils.get_default(oinfo, {}, default_converter())
    assert callable(result)
    assert result.__name__ == cli_utils.DEFAULT_SENTINEL_NAME
    assert result() is None


def test_get_default_cattrs_error() -> None:
    """
    "get_default()" checks if cattrs can convert a loaded default.
    """
    converter = default_converter()
    attrs.Attribute(  # type: ignore[call-arg,var-annotated]
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
    oinfo = types.OptionInfo(
        parent_cls=type,
        path="test",
        cls=List[int],
        default=attrs.NOTHING,
        has_no_default=True,
        default_is_factory=False,
    )
    with pytest.raises(ValueError, match="Invalid default for type"):
        cli_utils.get_default(
            oinfo,
            {"test": types.LoadedValue(["spam"], types.LoaderMeta("Dummy"))},
            converter,
        )


OPTIONAL_TEST_DATA = [
    (int, 3, (int, 3, None, (), False)),
    (int, cli_utils.NO_DEFAULT, (int, cli_utils.NO_DEFAULT, None, (), False)),
    (Optional[int], 3, (int, 3, None, (), True)),
    (Optional[int], None, (int, None, None, (), True)),
    (Optional[int], cli_utils.NO_DEFAULT, (int, None, None, (), True)),
    (Union[int, None], 3, (int, 3, None, (), True)),
    (Union[int, None], None, (int, None, None, (), True)),
    (Union[int, None], cli_utils.NO_DEFAULT, (int, None, None, (), True)),
    (Union[None, int], 3, (int, 3, None, (), True)),
    (Union[None, int], None, (int, None, None, (), True)),
    (Union[None, int], cli_utils.NO_DEFAULT, (int, None, None, (), True)),
    (List[int], None, (List[int], None, list, (int,), False)),
    (Optional[List[int]], None, (List[int], None, list, (int,), True)),
    (None, None, (None, None, None, (), False)),
]
if PY_310:
    OPTIONAL_TEST_DATA += [  # type: ignore[misc]  # type: ignore[misc]
        (int | None, 3, (int, 3, None, (), True)),
        (int | None, None, (int, None, None, (), True)),
        (int | None, cli_utils.NO_DEFAULT, (int, None, None, (), True)),
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
