"""
Additional attrs validators

.. deprecated:: 1.0.1
   Use :mod:`attrs.validators` instead.  Will be removed in 2.0.0.
"""
from attrs.validators import ge, gt, le, lt
from attrs.validators import max_len
from attrs.validators import max_len as maxlen


__all__ = [
    "lt",
    "le",
    "ge",
    "gt",
    "max_len",
    "maxlen",
]
