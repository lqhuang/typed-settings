"""
Helpers and wrappers for settings class backends.

Supported backends are:

- :mod:`dataclasses`
- `attrs <https://attrs.org>`_ (optional dependency)
- `pydantic <https://docs.pydantic.dev>`_ (optional dependency)
"""
import dataclasses
from itertools import groupby
from typing import Any, Dict, List, Optional, Protocol, Tuple, Type, cast

from . import constants, types
from ._compat import PY_39


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

    @staticmethod
    def asdict(inst: Any) -> types.SettingsDict:
        """
        Return the instances attributes as dict, recurse into nested classes of the
        same kind.
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

        result: List[types.OptionInfo] = []

        def iter_attribs(r_cls: type, prefix: str) -> None:
            r_cls = attrs.resolve_types(r_cls)  # type: ignore[type-var]
            for field in attrs.fields(r_cls):  # type: ignore[misc]
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
                        metadata=field.metadata.get(constants.METADATA_KEY, {}),
                    )
                    result.append(oinfo)

        iter_attribs(cls, "")
        return tuple(result)

    @staticmethod
    def fields_to_parent_classes(cls: type) -> Dict[str, type]:
        import attrs

        return {
            field.name: (field.type if attrs.has(field.type) else cls)
            for field in attrs.fields(cls)  # type: ignore[misc]
        }

    @staticmethod
    def asdict(inst: Any) -> types.SettingsDict:
        import attrs

        return attrs.asdict(inst)


class Dataclasses:
    """
    Handler for :mod:`dataclasses` classes.
    """

    @staticmethod
    def check(cls: type) -> bool:
        return dataclasses.is_dataclass(cls)

    @classmethod
    def iter_fields(self, cls: type) -> types.OptionList:
        result: List[types.OptionInfo] = []

        def iter_attribs(r_cls: type, prefix: str) -> None:
            r_cls = self.resolve_types(r_cls)  # type: ignore[type-var]
            for field in dataclasses.fields(r_cls):
                if field.init is False:
                    continue
                if field.type is not None and dataclasses.is_dataclass(field.type):
                    iter_attribs(field.type, f"{prefix}{field.name}.")
                else:
                    is_nothing = field.default is dataclasses.MISSING
                    is_factory = (
                        is_nothing and field.default_factory is not dataclasses.MISSING
                    )
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
                        converter=None,
                        metadata=field.metadata.get(constants.METADATA_KEY, {}),
                    )
                    result.append(oinfo)

        iter_attribs(cls, "")
        return tuple(result)

    @staticmethod
    def fields_to_parent_classes(cls: type) -> Dict[str, type]:
        return {
            field.name: (field.type if dataclasses.is_dataclass(field.type) else cls)
            for field in dataclasses.fields(cls)
        }

    @staticmethod
    def asdict(inst: Any) -> types.SettingsDict:
        return dataclasses.asdict(inst)

    @staticmethod
    def resolve_types(
        cls: Type[types.T],
        globalns: Optional[Dict[str, Any]] = None,
        localns: Optional[Dict[str, Any]] = None,
        include_extras: bool = True,
    ) -> Type[types.T]:
        """
        Resolve any strings and forward annotations in type annotations.

        This is only required if you need concrete types in fields' *type* field. In
        other words, you don't need to resolve your types if you only use them for
        static type checking.

        With no arguments, names will be looked up in the module in which the class was
        created. If this is not what you want, e.g. if the name only exists inside
        a method, you may pass *globalns* or *localns* to specify other dictionaries in
        which to look up these names. See the docs of `typing.get_type_hints` for more
        details.

        Args:
            cls: Class to resolve.
            globalns: Dictionary containing global variables.
            localns: Dictionary containing local variables.
            include_extras: Resolve more accurately, if possible.
                Pass ``include_extras`` to ``typing.get_hints``, if supported by the
                typing module. On supported Python versions (3.9+), this resolves the
                types more accurately.

        Return:
            *cls* so you can use this function also as a class decorator.
            Please note that you have to apply it **after** `attrs.define`. That
            means the decorator has to come in the line **before** `attrs.define`.
        """
        # Since calling get_type_hints is expensive we cache whether we've
        # done it already.
        if getattr(cls, "__dataclass_types_resolved__", None) != cls:
            import typing

            kwargs: Dict[str, Any] = {"globalns": globalns, "localns": localns}

            if PY_39:
                kwargs["include_extras"] = include_extras

            hints = typing.get_type_hints(cls, **kwargs)
            for field in dataclasses.fields(cls):  # type: ignore[arg-type]
                if field.name in hints:  # pragma: no cover
                    # Since fields have been frozen we must work around it.
                    object.__setattr__(field, "type", hints[field.name])
            # We store the class we resolved so that subclasses know they haven't
            # been resolved.
            cls.__dataclass_types_resolved__ = cls  # type: ignore[attr-defined]

        # Return the class so you can use it as a decorator too.
        return cls


class Pydantic:
    """
    Handler for "Pydantic" classes.
    """

    @staticmethod
    def check(cls: type) -> bool:
        try:
            import pydantic

            return issubclass(cls, pydantic.BaseModel)
        except ImportError:
            return False

    @staticmethod
    def iter_fields(cls: type) -> types.OptionList:
        import pydantic

        result: List[types.OptionInfo] = []

        def iter_attribs(r_cls: type, prefix: str) -> None:
            for name, field in r_cls.model_fields.items():  # type: ignore[attr-defined]
                if (
                    field.annotation is not None
                    and isinstance(field.annotation, type)
                    and issubclass(field.annotation, pydantic.BaseModel)
                ):
                    iter_attribs(field.annotation, f"{prefix}{name}.")
                else:
                    json_schema_extra = field.json_schema_extra or {}
                    metadata = json_schema_extra.get("metadata", {})
                    oinfo = types.OptionInfo(
                        parent_cls=r_cls,
                        path=f"{prefix}{name}",
                        cls=field.annotation,  # type: ignore[arg-type]
                        is_secret=(
                            isinstance(field.annotation, type)
                            and (
                                issubclass(
                                    field.annotation,
                                    (
                                        pydantic.SecretBytes,
                                        pydantic.SecretStr,
                                        *types.SECRETS_TYPES,
                                    ),
                                )
                            )
                        ),
                        default=field.default,
                        has_no_default=field.is_required(),
                        default_is_factory=False,
                        converter=None,
                        metadata=metadata.get(constants.METADATA_KEY, {}),
                    )
                    result.append(oinfo)

        iter_attribs(cls, "")
        return tuple(result)

    @staticmethod
    def fields_to_parent_classes(cls: type) -> Dict[str, type]:
        import pydantic

        return {
            name: (
                field.annotation
                if issubclass(field.annotation, pydantic.BaseModel)
                else cls
            )
            for name, field in cls.model_fields.items()  # type: ignore[attr-defined]
        }

    @staticmethod
    def asdict(inst: Any) -> types.SettingsDict:
        return inst.dict()


CLASS_HANDLERS: List[Type[ClsHandler]] = [
    Attrs,
    Dataclasses,
    Pydantic,
]


def find_handler(cls: type) -> Type[ClsHandler]:
    """
    Return the proper class handler for *cls*.

    Args:
        cls: The settings class to find a handler for.

    Return:
        A :class:`ClsHandler` that works with *cls*.

    Raise:
        TypeError: If no class handler can be found for *cls*.
    """
    for cls_handler in CLASS_HANDLERS:
        if cls_handler.check(cls):
            return cls_handler

    raise TypeError(f"Cannot handle type: {cls}")


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
    cls_handler = find_handler(cls)
    return cls_handler.iter_fields(cls)


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
    cls_handler = find_handler(cls)
    fields_to_parents = cls_handler.fields_to_parent_classes(cls)

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
