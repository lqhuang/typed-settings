"""
Helpers and wrappers for settings class backends.

Supported backends are:

- :mod:`dataclasses`
- `attrs <https://attrs.org>`_ (optional dependency)
- `pydantic <https://docs.pydantic.dev>`_ (optional dependency)
"""
from itertools import groupby
from typing import Dict, List, Protocol, Tuple, cast

from . import types


class ClsHandler(Protocol):
    """
    **Protocol** that class handlers must implement.

    .. versionadded:: 23.1.0
    """

    @staticmethod
    def check(cls: type) -> bool:
        """
        Return a bool indicating whether *cls* belongs to the handler's class lib.
        """

    @staticmethod
    def iter_fields(cls: type) -> types.OptionList:
        """
        Recursively iterate the the fields of *cls* and return the
        :class:`.types.OptionInfo` instances for them.

        Fields of nested classes are only converted to :class:`.types.OptionInfo` if
        they were created by the same class lib.  For example, if the parent class is
        an attrs class, the attributes of nested dataclasses are not added to the list
        of options.
        """

    @staticmethod
    def fields_to_parent_classes(cls: type) -> Dict[str, type]:
        """
        Map a class' attribute names to a "parent class".

        This parent class is used to create CLI option groups.  Thus, if a field's
        type is another (nested) settings class, that class should be used.  Else,
        the class itself should be used.
        """


class Attrs:
    """
    Handler for "attrs" classes.
    """

    @staticmethod
    def check(cls: type) -> bool:
        try:
            import attrs

            return attrs.has(cls)
        except ImportError:
            return False

    @staticmethod
    def iter_fields(cls: type) -> types.OptionList:
        import attrs

        cls = attrs.resolve_types(cls)  # type: ignore[type-var]
        result: List[types.OptionInfo] = []

        def iter_attribs(r_cls: type, prefix: str) -> None:
            for field in attrs.fields(r_cls):
                if field.init is False:
                    continue
                if field.type is not None and attrs.has(field.type):
                    iter_attribs(field.type, f"{prefix}{field.name}.")
                else:
                    is_nothing = field.default is attrs.NOTHING
                    is_factory = isinstance(field.default, cast(type, attrs.Factory))
                    oinfo = types.OptionInfo(
                        parent_cls=r_cls,
                        path=f"{prefix}{field.name}",
                        cls=field.type,
                        is_secret=(
                            isinstance(field.repr, types.SecretRepr)
                            or (
                                isinstance(field.type, type)
                                and issubclass(field.type, types.SECRETS_TYPES)
                            )
                        ),
                        default=field.default,
                        has_no_default=is_nothing,
                        default_is_factory=is_factory,
                        converter=field.converter,
                        metadata=field.metadata.get(types.METADATA_KEY, {}),
                    )
                    result.append(oinfo)

        iter_attribs(cls, "")
        return tuple(result)

    @staticmethod
    def fields_to_parent_classes(cls: type) -> Dict[str, type]:
        import attrs

        return {
            field.name: (field.type if attrs.has(field.type) else cls)
            for field in attrs.fields(cls)
        }


# def is_dataclass(cls: type) -> bool:
#     """
#     adsf.
#     """
#     return dataclasses.is_dataclass(cls)


CLASS_HANDLERS: List[ClsHandler] = [
    Attrs,
]


def deep_options(cls: type) -> types.OptionList:
    """
    Recursively iterates *cls* and nested attrs classes and returns a flat
    list of *(path, Attribute, type)* tuples.

    Args:
        cls: The class whose attributes will be listed.

    Returns:
        The flat list of attributes of *cls* and possibly nested attrs classes.
        *path* is a dot (``.``) separted path to the attribute, e.g.
        ``"parent_attr.child_attr.grand_child_attr``.

    Raises:
        NameError: if the type annotations can not be resolved.  This is, e.g., the
        case when recursive classes are being used.
    """
    for cls_handler in CLASS_HANDLERS:
        if cls_handler.check(cls):
            return cls_handler.iter_fields(cls)

    raise TypeError(f"Cannot handle type: {type(cls)}")


def group_options(
    cls: type, options: types.OptionList
) -> List[Tuple[type, types.OptionList]]:
    """
    Group (nested) options by parent class.

    If *cls* does not contain nested settings classes, return a single group for *cls*
    with all its options.

    If *cls* only contains nested subclasses, return one group per class containing all
    of that classes (posibly nested) options.

    If *cls* has multiple attributtes with the same nested settings class, create one
    group per attribute.

    If *cls* contains a mix of scalar options and nested options, return a mix of both.
    Scalar options schould be grouped (on top or bottom) or else multiple groups for the
    main settings class will be created.

    See the tests for details.

    Args:
        cls: The settings class
        options: The list of all options of the settings class.

    Return:
        A list of tuples matching a grouper class to all settings within that group.
    """
    for cls_handler in CLASS_HANDLERS:
        if cls_handler.check(cls):
            fields_to_parents = cls_handler.fields_to_parent_classes(cls)
            break
    else:
        raise TypeError(f"Cannot handle type: {type(cls)}")

    def keyfn(o: types.OptionInfo) -> Tuple[str, type]:
        """
        Group by prefix and also return the corresponding group class.
        """
        basename, *remainder = o.path.split(".")
        prefix = basename if remainder else ""
        return prefix, fields_to_parents[basename]

    grouper = groupby(options, key=keyfn)
    grouped_options = [(g_cls[1], tuple(g_opts)) for g_cls, g_opts in grouper]
    return grouped_options
