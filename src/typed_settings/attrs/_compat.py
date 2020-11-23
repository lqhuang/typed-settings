import sys


if sys.version_info[:2] >= (3, 8):
    from typing import get_args, get_origin
else:
    import collections.abc
    from typing import Generic, _GenericAlias

    def get_origin(tp):
        # Backported from py38
        if isinstance(tp, _GenericAlias):
            return tp.__origin__
        if tp is Generic:  # pragma: no cover
            return Generic
        return None

    def get_args(tp):
        # Backported from py38
        if isinstance(tp, _GenericAlias) and not tp._special:
            res = tp.__args__
            if (  # pragma: no cover
                get_origin(tp) is collections.abc.Callable
                and res[0] is not Ellipsis  # noqa: W503
            ):
                res = (list(res[:-1]), res[-1])  # pragma: no cover
            return res
        return ()


__all__ = ["get_args", "get_origin"]
