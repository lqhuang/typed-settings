"""
Tests for `typed_settings.attrs.converters`.
"""
import dataclasses
import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import attrs
import cattrs
import pydantic
import pytest

from typed_settings import converters
from typed_settings._compat import PY_39, PY_310
from typed_settings.cls_attrs import option, secret, settings


def custom_converter(v: Union[str, Path]) -> Path:
    """A custom converter for attrs fields."""
    return Path(v).resolve()


class LeEnum(Enum):
    """A simple enum for testing."""

    spam = "Le Spam"
    eggs = "Le Eggs"


@dataclasses.dataclass
class DataCls:
    """A basic "dataclass" for testing."""

    u: str
    p: str


@settings
class AttrsCls:
    """A basic "attrs" class for testing."""

    u: str = option()
    p: str = secret()


class PydanticCls(pydantic.BaseModel):
    """A basic Pydantic class."""

    u: str
    p: str


@dataclasses.dataclass
class ChildDc:
    """A simple nested class."""

    x: int
    y: Path


@dataclasses.dataclass(frozen=True)
class ParentDc:
    """A rather complex class with various scalar and composite attribute types."""

    child: ChildDc
    a: float
    c: LeEnum
    d: datetime
    e: List[ChildDc]
    f: Set[datetime]
    b: float = dataclasses.field(default=3.14)


@attrs.frozen
class ChildAttrs:
    """A simple nested class."""

    x: int
    y: Path = attrs.field(converter=custom_converter)


@attrs.frozen(kw_only=True)
class ParentAttrs:
    """A rather complex class with various scalar and composite attribute types."""

    child: ChildAttrs
    a: float
    b: float = attrs.field(default=3.14, validator=attrs.validators.le(2))
    c: LeEnum
    d: datetime
    e: List[ChildAttrs]
    f: Set[datetime]


class ChildPydantic(pydantic.BaseModel):
    """A simple nested class."""

    x: int
    y: Path


class ParentPydantic(pydantic.BaseModel):
    """A rather complex class with various scalar and composite attribute types."""

    child: ChildPydantic
    a: float
    b: float = pydantic.Field(default=3.14, le=2)
    c: LeEnum
    d: datetime
    e: List[ChildPydantic]
    f: Set[datetime]


Example3T = List[Tuple[str, Any, Any]]  # 3-tuple example
Example4T = List[Tuple[str, Any, Any, Any]]  # 4-tuple example

# This list is filled with examples for each supported data type below.
# It is used to check that all supported converters can convert the same data.
SUPPORTED_TYPES_DATA: Example4T = []

# Any - types remain unchanged
SUPPORTED_ANY: Example3T = [
    ("Any(int)", 2, 2),
    ("Any(str)", "2", "2"),
    ("Any(None)", None, None),
]
SUPPORTED_TYPES_DATA += [(n, v, e, Any) for n, v, e in SUPPORTED_ANY]

# bool - can be parsed from a defined set of values
SUPPORTED_BOOL: Example3T = [
    ("bool(True)", True, True),
    ("bool('True')", "True", True),
    ("bool('True')", "TRUE", True),
    ("bool('true')", "true", True),
    ("bool('true')", "t", True),
    ("bool('yes')", "yes", True),
    ("bool('yes')", "Y", True),
    ("bool('yes')", "on", True),
    ("bool('1')", "1", True),
    ("bool(1)", 1, True),
    ("bool(False)", False, False),
    ("bool('False')", "False", False),
    ("bool('False')", "fAlse", False),  # sic!
    ("bool('false')", "false", False),
    ("bool('no')", "NO", False),
    ("bool('no')", "n", False),
    ("bool('no')", "OFF", False),
    ("bool('0')", "0", False),
    ("bool(0)", 0, False),
]
SUPPORTED_TYPES_DATA += [(n, v, e, bool) for n, v, e in SUPPORTED_BOOL]

# int, float, str - nothing special about these ...
SUPPORTED_STDTYPES: Example4T = [
    # Nothing special about these ...
    ("int(23)", 23, 23, int),
    ("int('42')", "42", 42, int),
    ("float(3.14)", 3.14, 3.14, float),
    ("float('.815')", ".815", 0.815, float),
    ("str('spam')", "spam", "spam", str),
]
SUPPORTED_TYPES_DATA += SUPPORTED_STDTYPES

# datetime - can be parsed from a limit set of ISO formats
SUPPORTED_DATETIME: Example3T = [
    ("datetime(naive-space)", "2020-05-04 13:37:00", datetime(2020, 5, 4, 13, 37)),
    ("datetime(naive-T)", "2020-05-04T13:37:00", datetime(2020, 5, 4, 13, 37)),
    (
        "datetime(tz-Z)",
        "2020-05-04T13:37:00Z",
        datetime(2020, 5, 4, 13, 37, tzinfo=timezone.utc),
    ),
    (
        "datetime(tz-offset-utc)",
        "2020-05-04T13:37:00+00:00",
        datetime(2020, 5, 4, 13, 37, tzinfo=timezone.utc),
    ),
    (
        "datetime(tz-offset-2h)",
        "2020-05-04T13:37:00+02:00",
        datetime(2020, 5, 4, 13, 37, tzinfo=timezone(timedelta(seconds=7200))),
    ),
    ("datetime(inst)", datetime(2020, 5, 4, 13, 37), datetime(2020, 5, 4, 13, 37)),
]
SUPPORTED_TYPES_DATA += [(n, v, e, datetime) for n, v, e in SUPPORTED_DATETIME]

# Enum - Enums are parsed from their "key"
SUPPORTED_ENUM: Example3T = [
    ("enum(str)", "eggs", LeEnum.eggs),
    ("enum(inst)", LeEnum.eggs, LeEnum.eggs),
]
SUPPORTED_TYPES_DATA += [(n, v, e, LeEnum) for n, v, e in SUPPORTED_ENUM]

# Path - Paths are resolved by default
SUPPORTED_PATH = [
    ("path(str)", "spam", Path.cwd().joinpath("spam")),
    ("path(inst)", Path("eggs"), Path.cwd().joinpath("eggs")),
]
SUPPORTED_TYPES_DATA += [(n, v, e, Path) for n, v, e in SUPPORTED_PATH]

# list
SUPPORTED_LIST: Example4T = [
    ("List[any]", [1, "2"], [1, "2"], List),
    ("list[any]", [1, "2"], [1, "2"], list),
    ("List[int]", [1, 2], [1, 2], List[int]),
    (
        "list[datetime]",
        ["2023-05-04T13:37:42+00:00"],
        [datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc)],
        List[datetime],
    ),
]
if PY_39:
    SUPPORTED_LIST += [
        ("list[int]", [1, "2"], [1, 2], list[int]),
    ]
SUPPORTED_TYPES_DATA += SUPPORTED_LIST

# tuple
SUPPORTED_TUPLE: Example4T = [
    ("tuple[any]", [1, "2"], (1, "2"), tuple),
    ("Tuple[Any]", [1, "2"], (1, "2"), Tuple),
    ("Tuple[int, ...]", [1, 2, "3"], (1, 2, 3), Tuple[int, ...]),
    ("Tuple[int, float]", [1, "2.3"], (1, 2.3), Tuple[int, float]),
    (
        "list[datetime]",
        ["2023-05-04T13:37:42+00:00"],
        (datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc),),
        Tuple[datetime],
    ),
]
if PY_39:
    SUPPORTED_TUPLE += [
        ("tuple[int, ...]", [1, 2, "3"], (1, 2, 3), tuple[int, ...]),
        ("tuple[int, float]", [1, "2.3"], (1, 2.3), tuple[int, float]),
    ]
SUPPORTED_TYPES_DATA += SUPPORTED_TUPLE

# dict
SUPPORTED_DICT: Example4T = [
    ("dict[any, any]", {"y": 1, "n": 3.1}, {"y": 1, "n": 3.1}, dict),
    ("Dict[Any, Any]", {"y": 1, "n": 3.1}, {"y": 1, "n": 3.1}, Dict),
    ("Dict[bool, int]", {"y": 1, "n": 3.1}, {True: 1, False: 3}, Dict[bool, int]),
    (
        "dict[str, datetime]",
        {"a": "2023-05-04T13:37:42+00:00"},
        {"a": datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc)},
        Dict[str, datetime],
    ),
]
if PY_39:
    SUPPORTED_DICT += [
        (
            "dict[bool, int]",
            {"y": 1, "n": 3.1},
            {True: 1, False: 3},
            dict[bool, int],
        ),
    ]
SUPPORTED_TYPES_DATA += SUPPORTED_DICT

# MappingProxy
SUPPORTED_MAPPINGPROXY: Example4T = []
if PY_39:
    SUPPORTED_MAPPINGPROXY += [
        (
            "MappingProxyType[Any, Any]",
            {"y": 1, "n": 3.1},
            MappingProxyType({"y": 1, "n": 3.1}),
            MappingProxyType,
        ),
        (
            "MappingProxyType[bool, int]",
            {"y": 1, "n": 3.1},
            MappingProxyType({True: 1, False: 3}),
            MappingProxyType[bool, int],
        ),
    ]
SUPPORTED_TYPES_DATA += SUPPORTED_MAPPINGPROXY

# set
SUPPORTED_SET: Example4T = [
    ("set[any]", [1, "2"], {1, "2"}, set),
    ("Set[any]", [1, "2"], {1, "2"}, Set),
    ("Set[int]", [1, 2], {1, 2}, Set[int]),
]
if PY_39:
    SUPPORTED_SET += [
        ("set[int]", [1, "2"], {1, 2}, set[int]),
    ]
SUPPORTED_TYPES_DATA += SUPPORTED_SET

# frozenset
SUPPORTED_FROZENSET: Example4T = [
    ("frozenset[any]", [1, "2"], frozenset({1, "2"}), frozenset),
    ("Frozenset[any]", [1, "2"], frozenset({1, "2"}), FrozenSet),
    ("Frozenset[int]", [1, 2], frozenset({1, 2}), FrozenSet[int]),
]
if PY_39:
    SUPPORTED_FROZENSET += [
        ("frozenset(int)", [1, "2"], frozenset({1, 2}), frozenset[int]),
    ]
SUPPORTED_TYPES_DATA += SUPPORTED_FROZENSET

# Union / Optional
SUPPORTED_UNION: Example4T = [
    ("Optional(None)", None, None, Optional[str]),
    ("Optional(int)", 1, "1", Optional[str]),
    ("dc|None(None)", None, None, Optional[DataCls]),
    ("dc|None(dict)", {"u": "u", "p": "p"}, DataCls("u", "p"), Optional[DataCls]),
    ("enum|None", "spam", LeEnum.spam, Optional[LeEnum]),
    # ("Union(None)", None, None, Union[None, S, List[str]]),
    # (
    #     "Union(attrs)",
    #     {"u": "u", "p": "p"},
    #     S("u", "p"),
    #     Union[None, S, List[str]],
    # ),
    # ("Union(list)", [1, 2], ["1", "2"], Union[None, S, List[str]]),
]
SUPPORTED_TYPES_DATA += SUPPORTED_UNION
if PY_310:
    SUPPORTED_UNION = [
        ("str|None(None)", None, None, str | None),
        ("str|None(int)", 1, "1", str | None),
        # (S | List[str], [1, 2], ["1", "2"], "attrs|list(list)"),
    ]

# attrs classes
SUPPORTED_ATTRSCLASSES: Example4T = [
    ("attrs(dict)", {"u": "user", "p": "pwd"}, AttrsCls("user", "pwd"), AttrsCls),
    ("attrs(inst)", AttrsCls("user", "pwd"), AttrsCls("user", "pwd"), AttrsCls),
    (
        "attrs(nested)",
        {
            "a": "3.14",
            "b": 1,
            "c": "eggs",
            "d": "2023-05-04T13:37:42+00:00",
            "e": [{"x": 0, "y": "a"}, {"x": 1, "y": "b"}],
            "f": ["2023-05-04T13:37:42+00:00", "2023-05-04T13:37:42+00:00"],
            "child": {"x": 3, "y": "c"},
        },
        ParentAttrs(
            a=3.14,
            b=1,
            c=LeEnum.eggs,
            d=datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc),
            e=[
                ChildAttrs(0, Path.cwd().joinpath("a")),
                ChildAttrs(1, Path.cwd().joinpath("b")),
            ],
            f={datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc)},
            child=ChildAttrs(3, Path.cwd().joinpath("c")),
        ),
        ParentAttrs,
    ),
]
SUPPORTED_TYPES_DATA += SUPPORTED_ATTRSCLASSES

# dataclasses
SUPPORTED_DATACLASSES: Example4T = [
    ("dc(dict)", {"u": "user", "p": "pwd"}, DataCls("user", "pwd"), DataCls),
    ("dc(inst)", DataCls("user", "pwd"), DataCls("user", "pwd"), DataCls),
    (
        "dc(nested)",
        {
            "a": "3.14",
            "b": 1,
            "c": "eggs",
            "d": "2023-05-04T13:37:42+00:00",
            "e": [{"x": 0, "y": "a"}, {"x": 1, "y": "b"}],
            "f": ["2023-05-04T13:37:42+00:00", "2023-05-04T13:37:42+00:00"],
            "child": {"x": 3, "y": "c"},
        },
        ParentDc(
            a=3.14,
            b=1,
            c=LeEnum.eggs,
            d=datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc),
            e=[
                ChildDc(0, Path.cwd().joinpath("a")),
                ChildDc(1, Path.cwd().joinpath("b")),
            ],
            f={datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc)},
            child=ChildDc(3, Path.cwd().joinpath("c")),
        ),
        ParentDc,
    ),
]
SUPPORTED_TYPES_DATA += list(SUPPORTED_DATACLASSES)

# Pydantic classes
SUPPORTED_PYDANTIC: Example4T = [
    (
        "pydantic(dict)",
        {"u": "user", "p": "pwd"},
        PydanticCls(u="user", p="pwd"),
        PydanticCls,
    ),
    (
        "pydantic(inst)",
        PydanticCls(u="user", p="pwd"),
        PydanticCls(u="user", p="pwd"),
        PydanticCls,
    ),
    (
        "pydantic(nested)",
        {
            "a": "3.14",
            "b": 1,
            "c": "Le Eggs",
            "d": "2023-05-04T13:37:42+00:00",
            "e": [{"x": 0, "y": "a"}, {"x": 1, "y": "b"}],
            "f": ["2023-05-04T13:37:42+00:00", "2023-05-04T13:37:42+00:00"],
            "child": {"x": 3, "y": "c"},
        },
        ParentPydantic(
            a=3.14,
            b=1,
            c=LeEnum.eggs,
            d=datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc),
            e=[
                ChildPydantic(x=0, y=Path("a")),
                ChildPydantic(x=1, y=Path("b")),
            ],
            f={datetime(2023, 5, 4, 13, 37, 42, tzinfo=timezone.utc)},
            child=ChildPydantic(x=3, y=Path("c")),
        ),
        ParentPydantic,
    ),
]
SUPPORTED_TYPES_DATA += list(SUPPORTED_PYDANTIC)


@pytest.mark.parametrize(
    "converter",
    [
        pytest.param(converters.get_default_cattrs_converter(), id="converter:cattrs"),
        pytest.param(converters.get_default_ts_converter(), id="converter:ts"),
    ],
)
@pytest.mark.parametrize(
    "value, typ, expected",
    [pytest.param(v, t, e, id=n) for n, v, e, t in SUPPORTED_TYPES_DATA],
)
def test_supported_types(
    converter: converters.Converter, value: Any, typ: type, expected: Any
) -> None:
    """
    All officially supported types can be converted.

    The list :data:`SUPPORTED_TYPES_DATA` is the officially source of truth.

    Please create an issue if something is missing here.
    """
    assert converter.structure(value, typ) == expected


@pytest.mark.parametrize(
    "converter",
    [
        pytest.param(converters.get_default_cattrs_converter, id="converter:cattrs"),
        pytest.param(converters.get_default_ts_converter, id="converter:ts"),
    ],
)
@pytest.mark.parametrize(
    "value, expected", [pytest.param(v, e, id=n) for n, v, e in SUPPORTED_PATH]
)
@pytest.mark.parametrize("resolve_paths", [True, False])
def test_resolve_path(
    converter: Callable[[bool], converters.Converter],
    value: Any,
    expected: Any,
    resolve_paths: bool,
) -> None:
    """
    The path-resolving behavior can be explicitly set.
    """
    if not resolve_paths:
        expected = expected.relative_to(Path.cwd())
    c = converter(resolve_paths)
    assert c.structure(value, Path) == expected


@pytest.mark.parametrize(
    "cls, value",
    [
        # "to_bool()" is flexible, but does not accept anything
        (bool, ""),
        (bool, []),
        (bool, "spam"),
        (bool, 2),
        (bool, -1),
        (datetime, 3),
        # len(value) does not match len(tuple-args)
        (Tuple[int, int], (1,)),
        (Tuple[int, int], (1, 2, 3)),
        (Union[int, datetime, None], "3.1"),  # float is not part of the Union
        (Sequence, [0, 1]),  # Type not supported
        (AttrsCls, {"foo": 3}),  # Invalid attribute
        (AttrsCls, {"opt", "x"}),  # Invalid value
        (DataCls, {"foo": 3}),  # Invalid attribute
        (DataCls, {"opt", "x"}),  # Invalid value
        (PydanticCls, {"foo": 3}),  # Invalid attribute
        (PydanticCls, {"opt", "x"}),  # Invalid value
    ],
)
def test_unsupported_values(value: Any, cls: type) -> None:
    """
    Unsupported input leads to low level exceptions.  These are later unified by
    "_core.convert()".
    """
    converter = converters.TSConverter()
    with pytest.raises((KeyError, TypeError, ValueError)):
        converter.structure(value, cls)


STRLIST_TEST_DATA = [
    (List[int], [1, 2, 3]),
    (Set[int], {1, 2, 3}),
    (FrozenSet[int], frozenset({1, 2, 3})),
    (Tuple[int, ...], (1, 2, 3)),
    (Tuple[int, int, int], (1, 2, 3)),
]

if PY_39:
    STRLIST_TEST_DATA.extend(
        [
            (list[int], [1, 2, 3]),
            (set[int], {1, 2, 3}),
            (tuple[int, ...], (1, 2, 3)),
        ]
    )


@pytest.mark.parametrize("cls_decorator", [attrs.frozen, dataclasses.dataclass])
@pytest.mark.parametrize(
    "input, kw", [("1:2:3", {"sep": ":"}), ("[1,2,3]", {"fn": json.loads})]
)
@pytest.mark.parametrize("typ, expected", STRLIST_TEST_DATA)
def test_cattrs_strlist_hook(
    cls_decorator: Callable, input: str, kw: dict, typ: type, expected: Any
) -> None:
    """
    The strlist hook for can be configured with a separator string or a function.
    """

    @cls_decorator
    class Settings:
        a: typ  # type: ignore

    converter = converters.get_default_cattrs_converter()
    converters.register_strlist_hook(converter, **kw)
    result = converter.structure({"a": input}, Settings)
    assert result == Settings(expected)  # type: ignore[call-arg]


def test_cattrs_strlist_hook_either_arg() -> None:
    """
    Either "sep" OR "fn" can be passed to "register_str_list_hook()".
    """
    converter = converters.get_default_cattrs_converter()
    with pytest.raises(ValueError, match="You may either pass"):
        converters.register_strlist_hook(
            converter, sep=":", fn=lambda v: [v]
        )  # pragma: no cover


@pytest.mark.parametrize("cls_decorator", [attrs.frozen, dataclasses.dataclass])
@pytest.mark.parametrize(
    "input, sep", [("1:2:3", ":"), ("[1,2,3]", json.loads), ("123", None)]
)
@pytest.mark.parametrize("typ, expected", STRLIST_TEST_DATA)
def test_ts_strlist_hook(
    cls_decorator: Callable,
    input: str,
    sep: Union[str, Callable],
    typ: type,
    expected: Any,
) -> None:
    """
    The TSConverter has a builtin strlist hook that takes a separator string or a
    function.  It can be disabled with ``None``.
    """

    @cls_decorator
    class Settings:
        a: typ  # type: ignore

    converter = converters.TSConverter(strlist_sep=sep)
    result = converter.structure({"a": input}, Settings)
    assert result == Settings(expected)  # type: ignore[call-arg]


def test_get_default_converter_cattrs_installed() -> None:
    """
    If cattrs is installed, a cattrs converter is used by default.
    """
    converter = converters.default_converter()
    assert isinstance(converter, cattrs.Converter)


def test_get_default_converter_cattrs_uninstalled(
    unimport: Callable[[str], None]
) -> None:
    """
    If cattrs is not installed, the builtin converter is used by default.
    """
    unimport("cattrs")
    converter = converters.default_converter()
    assert isinstance(converter, converters.TSConverter)


def test_get_cattrs_converter_uninstalled(unimport: Callable[[str], None]) -> None:
    """
    An exception is raised by "get_default_cattrs_converter()" if  cattrs is not
    installed.
    """
    unimport("cattrs")
    with pytest.raises(ModuleNotFoundError):
        converters.get_default_cattrs_converter()
