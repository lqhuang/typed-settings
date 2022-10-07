"""
Addtional attrs hooks
"""
from datetime import datetime
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Any, List

import attrs

from ..converters import BaseConverter, default_converter
from ..types import SettingsClass


if TYPE_CHECKING:
    try:
        from attr import Attribute, _FieldTransformer  # type: ignore
    except ImportError:
        # Just in case the symbols are moved from "attr" to "attrs"
        from attrs import Attribute, _FieldTransformer  # type: ignore


__all__ = [
    "auto_convert",
    "auto_serialize",
    "make_auto_converter",
]


def make_auto_converter(converter: BaseConverter) -> "_FieldTransformer":
    """
    Creates and returns an auto-converter `field transformer`_.

    .. _field transformer: https://www.attrs.org/en/stable/extending.html
                        #automatic-field-transformation-and-modification

    Args:
        converters: A cattrs :class:`~cattrs.Converter` that can handle the
            types of all fields.

    Returns:
        A function that can be passed as *field_transformer* to
        :func:`attrs.define()`.

    Example:

        .. code-block:: python

            >>> from datetime import datetime
            >>> from pathlib import Path
            >>>
            >>> import attrs
            >>> import cattrs
            >>>
            >>> converter = cattrs.Converter()
            >>> converter.register_structure_hook(
            ...     datetime, lambda v, _t: datetime.fromisoformat(v)
            ... )
            >>> converter.register_structure_hook(Path, lambda v, t: t(v))
            >>>
            >>> auto_convert = make_auto_converter(converter)
            >>>
            >>> @attrs.define(field_transformer=auto_convert)
            ... class C:
            ...     a: Path
            ...     b: datetime
            ...
            >>> inst = C(a="spam.md", b="2020-05-04")
            >>> inst
            C(a=PosixPath('spam.md'), b=datetime.datetime(2020, 5, 4, 0, 0))
            >>> inst.b = "2022-01-01"
            >>> inst
            C(a=PosixPath('spam.md'), b=datetime.datetime(2022, 1, 1, 0, 0))

    """

    def auto_convert(
        cls: SettingsClass, attribs: List["Attribute[Any]"]
    ) -> List["Attribute[Any]"]:
        """
        A field transformer that tries to convert all attribs of a class to
        their annotated type.
        """
        attrs.resolve_types(cls, attribs=attribs)
        results = []
        for attrib in attribs:
            # Do not override explicitly defined converters!
            if attrib.converter is None:
                c = partial(converter.structure, cl=attrib.type)
                attrib = attrib.evolve(converter=c)
            results.append(attrib)

        return results

    return auto_convert


auto_convert = make_auto_converter(default_converter())
"""
An Attrs `field transformer`_ that adds converters to attributes based on their
type.

It uses the :func:`.default_converter()`.

*Deprecated:* Use ``cattrs.structure()`` instead.
"""


def auto_serialize(_inst: Any, _attrib: "Attribute[Any]", value: Any) -> Any:
    """
    Inverse hook to :func:`auto_convert` for use with :func:`attrs.asdict()`.

    *Deprecated:* Use ``cattrs.unstructure()`` instead.
    """
    if isinstance(value, datetime):
        return datetime.isoformat(value)
    if isinstance(value, Enum):
        return value.name
    return value
