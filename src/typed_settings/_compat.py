import sys
from typing import Any, Optional, Tuple


PY_38 = sys.version_info[:2] >= (3, 8)
PY_39 = sys.version_info[:2] >= (3, 9)
PY_310 = sys.version_info[:2] >= (3, 10)
PY_311 = sys.version_info[:2] >= (3, 11)


if PY_38:
    from typing import Final, Protocol, get_args, get_origin
else:
    import collections.abc
    from typing import Generic, _GenericAlias  # type: ignore
    from typing import _Protocol as Protocol  # type: ignore

    from typing_extensions import Final  # type: ignore

    def get_origin(tp: Any) -> Optional[Any]:
        # Backported from py38
        if isinstance(tp, _GenericAlias):
            return tp.__origin__
        if tp is Generic:  # pragma: no cover
            return Generic
        return None

    def get_args(tp: Any) -> Tuple[Any, ...]:
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


__all__ = ["Final", "Protocol", "get_args", "get_origin"]
