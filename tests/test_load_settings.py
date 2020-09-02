from pathlib import Path
from typing import List

from attr import frozen, field
import pytest

import typed_settings as ts


@frozen
class Host:
    name: str
    port: int = field(converter=int)


@frozen(kw_only=True)
class Settings:
    url: str
    default: int = 3
    host: Host = field(converter=lambda d: Host(**d) if isinstance(d, dict) else d)


def test_load_settings(tmp_path, monkeypatch):
    """Test basic functionality"""
    monkeypatch.setenv('EXAMPLE_HOST_PORT', '42')

    config_file = tmp_path.joinpath('settings.toml')
    config_file.write_text("""[example]
        url = "https://example.com"
        [example.host]
        name = "example.com"
        port = 443
    """)

    settings = ts.load_settings(
        settings_cls=Settings, appname='example', config_files=[config_file]
    )
    assert settings == Settings(
        url='https://example.com',
        default=3,
        host=Host(
            name='example.com',
            port=42,
        ),
    )


@pytest.fixture
def fnames(tmp_path: Path) -> List[Path]:
    p0 = tmp_path.joinpath('0.toml')
    p1 = tmp_path.joinpath('1.toml')
    p2 = tmp_path.joinpath('2')
    p3 = tmp_path.joinpath('3')
    p0.touch()
    p2.touch()
    return [p0, p1, p2, p3]

@pytest.mark.parametrize('cfn, env, expected', [
    ([], None, []),
    ([0], None, [0]),
    ([1], None, []),
    ([2], None, [2]),
    ([3], None, []),
    ([], [0], [0]),
    ([0, 1], [2, 3], [0, 2]),
])
def test_no_paths(cfn, env, expected, fnames, monkeypatch):
    if env is not None:
        monkeypatch.setenv('CF', ':'.join(str(fnames[i]) for i in env))
        env = 'CF'

    paths = ts._get_config_filenames([fnames[i] for i in cfn], env)
    assert paths == [fnames[i] for i in expected]


def test_dict_merge():
    """Dicts must be merged recursively.  Lists are just overridden."""
    d1 = {
        '1a': 3,
        '1b': {'2a': 'spam', '2b': {'3a': 'foo'}},
        '1c': [{'2a': 3.14}, {'2b': 34.3}],
        '1d': 4,
    }
    d2 = {
        '1b': {'2a': 'eggs', '2b': {'3b': 'bar'}},
        '1c': [{'2a': 23}, {'2b': 34.3}],
        '1d': 5,
    }
    ts._merge_dicts(d1, d2)
    assert d1 == {
        '1a': 3,
        '1b': {'2a': 'eggs', '2b': {'3a': 'foo', '3b': 'bar'}},
        '1c': [{'2a': 23}, {'2b': 34.3}],
        '1d': 5,
    }


def test_clean_settings():
    """Settings for which there is no attribute must be recursively removed."""
    settings = {
        'url': 'abc',
        'host': {'port': 23, 'eggs': 42},
        'spam': 23,
    }
    result = ts._clean_settings(settings, Settings)
    assert result == {
        'url': 'abc',
        'host': {'port': 23},
    }


def test_clean_settings_unresolved_type():
    """Cleaning must also work if an options type is an unresolved string."""
    @frozen
    class Host:
        port: int = field(converter=int)


    @frozen(kw_only=True)
    class Settings:
        host: 'Host' = field(converter=lambda d: Host(**d) if isinstance(d, dict) else d)

    settings = {'host': {'port': 23, 'eggs': 42}}
    result = ts._clean_settings(settings, Settings)
    assert result == {'host': {'port': 23}}


def test_get_env_dict():
    env = {
        'T_URL': 'foo',
        'T_HOST': 'spam',  # Haha! Just a deceit!
        'T_HOST_PORT': '25',
    }
    settings = ts._get_env_dict(Settings, env, 'T_')
    assert settings == {
        'url': 'foo',
        'host': {
            'port': '25',
        },
    }
