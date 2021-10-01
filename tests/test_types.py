from typed_settings import types


def test_auto_singleton():
    """
    `_Auto()`  is a singleton.
    """
    assert types._Auto() is types.AUTO


def test_auto_repr():
    """
    `_Auto()` has a nice repr.
    """
    assert repr(types._Auto()) == "AUTO"
