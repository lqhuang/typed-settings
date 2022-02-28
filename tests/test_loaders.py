import textwrap
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import toml
from pytest import MonkeyPatch

from typed_settings._dict_utils import _deep_options
from typed_settings.attrs import settings
from typed_settings.exceptions import (
    ConfigFileLoadError,
    ConfigFileNotFoundError,
    InvalidOptionsError,
    UnknownFormatError,
)
from typed_settings.loaders import (
    EnvLoader,
    FileFormat,
    FileLoader,
    InstanceLoader,
    PythonFormat,
    TomlFormat,
    clean_settings,
)
from typed_settings.types import OptionList


@settings(frozen=True)
class Host:
    name: str
    port: int


@settings(frozen=True)
class Settings:
    host: Host
    url: str
    default: int = 3


class TestCleanSettings:
    """Tests for clean_settings."""

    def test_load_convert_dashes(self):
        """
        Dashes in settings and section names are replaced with underscores.
        """

        @settings(frozen=True)
        class Sub:
            b_1: str

        @settings(frozen=True)
        class Settings:
            a_1: str
            a_2: str
            sub_section: Sub

        s = {
            "a-1": "spam",
            "a_2": "eggs",
            "sub-section": {"b-1": "bacon"},
        }

        result = clean_settings(s, _deep_options(Settings), "test")
        assert result == {
            "a_1": "spam",
            "a_2": "eggs",
            "sub_section": {"b_1": "bacon"},
        }

    def test_no_replace_dash_in_dict_keys(self):
        """
        "-" in TOML keys are replaced with "_" for sections and options, but
        "-" in actuall dict keys are left alone.

        See: https://gitlab.com/sscherfke/typed-settings/-/issues/3
        """

        @settings(frozen=True)
        class Settings:
            option_1: Dict[str, Any]
            option_2: Dict[str, Any]

        s = {
            "option-1": {"my-key": "val1"},
            "option-2": {"another-key": 23},
        }

        result = clean_settings(s, _deep_options(Settings), "test")
        assert result == {
            "option_1": {"my-key": "val1"},
            "option_2": {"another-key": 23},
        }

    def test_invalid_settings(self):
        """
        Settings for which there is no attribute are errors
        """

        s = {
            "url": "abc",
            "host": {"port": 23, "eggs": 42},
            "spam": 23,
        }
        with pytest.raises(InvalidOptionsError) as exc_info:
            clean_settings(s, _deep_options(Settings), "t")
        assert str(exc_info.value) == (
            "Invalid options found in t: host.eggs, spam"
        )

    def test_clean_settings_unresolved_type(self):
        """
        Cleaning must also work if an options type is an unresolved string.
        """

        @settings(frozen=True)
        class Host:
            port: int

        @settings(frozen=True)
        class Settings:
            host: "Host"

        s = {"host": {"port": 23, "eggs": 42}}
        with pytest.raises(InvalidOptionsError) as exc_info:
            clean_settings(s, _deep_options(Settings), "t")
        assert str(exc_info.value) == "Invalid options found in t: host.eggs"

    def test_clean_settings_dict_values(self):
        """
        Some dicts may be actual values (not nested) classes.  Don't try to
        check theses as option paths.
        """

        @settings(frozen=True)
        class Settings:
            option: Dict[str, Any]

        s = {"option": {"a": 1, "b": 2}}
        clean_settings(s, _deep_options(Settings), "t")


class TestPythonFormat:
    """Tests for PythonFormat"""

    @pytest.mark.parametrize(
        "fmt, data",
        [
            (
                PythonFormat("example"),
                """\
                class example:
                    url = "spam"

                    class host:
                        port = 42
                """,
            ),
            (
                PythonFormat("EXAMPLE", key_transformer=PythonFormat.to_lower),
                """\
                class EXAMPLE:
                    URL = "spam"

                    class HOST:
                        PORT = 42
                """,
            ),
            (
                PythonFormat("example", flat=True),
                """\
                class example:
                    url = "spam"
                    host_port = 42
                """,
            ),
            (
                PythonFormat(
                    "EXAMPLE", key_transformer=PythonFormat.to_lower, flat=True
                ),
                """\
                class EXAMPLE:
                    URL = "spam"
                    HOST_PORT = 42
                """,
            ),
        ],
    )
    def test_load_python(self, fmt: FileFormat, data: str, tmp_path: Path):
        """
        We can load settings from a Python file.
        """
        config_file = tmp_path.joinpath("settings.py")
        config_file.write_text(textwrap.dedent(data))
        result = fmt(config_file, Settings, _deep_options(Settings))
        assert result == {
            "url": "spam",
            "host": {"port": 42},
        }

    @pytest.mark.parametrize("section", ["example", "spam.example"])
    def test_section_not_found(self, section: str, tmp_path: Path):
        """
        An empty dict is returned when the config file does not contain the
        desired class.
        """
        config_file = tmp_path.joinpath("settings.py")
        config_file.write_text("class spam:\n    a = 'spam'\n")
        result = PythonFormat(section)(
            config_file, Settings, _deep_options(Settings)
        )
        assert result == {}

    def test_file_not_found(self):
        """
        "ConfigFileNotFoundError" is raised when a file does not exist.
        """
        pytest.raises(
            ConfigFileNotFoundError,
            PythonFormat(""),
            Path("x"),
            _deep_options(Settings),
            Settings,
        )

    def test_file_invalid(self, tmp_path: Path):
        """
        "ConfigFileLoadError" is raised when a file contains invalid Python.
        """
        config_file = tmp_path.joinpath("settings.py")
        config_file.write_text("3x = 'spam")
        pytest.raises(
            ConfigFileLoadError,
            PythonFormat(""),
            config_file,
            _deep_options(Settings),
            Settings,
        )


class TestTomlFormat:
    """Tests for TomlFormat"""

    @pytest.mark.parametrize(
        "fmt, data",
        [
            (
                TomlFormat("example"),
                """\
                [example]
                url = "spam"
                [example.host]
                port = 42
                """,
            ),
        ],
    )
    def test_load_toml(self, fmt: FileFormat, data: str, tmp_path: Path):
        """
        We can load settings from a TOML file.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(textwrap.dedent(data))
        result = fmt(config_file, Settings, _deep_options(Settings))
        assert result == {
            "url": "spam",
            "host": {"port": 42},
        }

    def test_load_from_nested(self, tmp_path: Path):
        """
        We can load settings from a nested section (e.g., "tool.example").
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[tool.example]
            a = "spam"
            [tool.example.sub]
            b = "eggs"
        """
        )
        result = TomlFormat("tool.example")(
            config_file,
            Settings,
            _deep_options(Settings),
        )
        assert result == {
            "a": "spam",
            "sub": {"b": "eggs"},
        }

    @pytest.mark.parametrize("section", ["example", "tool.example"])
    def test_section_not_found(self, section: str, tmp_path: Path):
        """
        An empty dict is returned when the config file does not contain the
        desired section.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[tool]
            a = "spam"
        """
        )
        result = TomlFormat(section)(
            config_file, Settings, _deep_options(Settings)
        )
        assert result == {}

    def test_file_not_found(self):
        """
        "ConfigFileNotFoundError" is raised when a file does not exist.
        """
        pytest.raises(
            ConfigFileNotFoundError,
            TomlFormat(""),
            Path("x"),
            _deep_options(Settings),
            Settings,
        )

    def test_file_not_allowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """
        "ConfigFileLoadError" is raised when a file cannot be accessed.
        """

        def toml_load(path: Path):
            raise PermissionError()

        monkeypatch.setattr(toml, "load", toml_load)

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[tool]
            a = "spam"
        """
        )

        pytest.raises(
            ConfigFileLoadError,
            TomlFormat(""),
            config_file,
            _deep_options(Settings),
            Settings,
        )

    def test_file_invalid(self, tmp_path: Path):
        """
        "ConfigFileLoadError" is raised when a file contains invalid TOML.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text("spam")
        pytest.raises(
            ConfigFileLoadError,
            TomlFormat(""),
            config_file,
            _deep_options(Settings),
            Settings,
        )


class TestFileLoader:
    """Tests for FileLoader"""

    @pytest.fixture
    def fnames(self, tmp_path: Path) -> List[Path]:
        p0 = tmp_path.joinpath("0.toml")
        p1 = tmp_path.joinpath("1.toml")
        p2 = tmp_path.joinpath("2")
        p3 = tmp_path.joinpath("3")
        p0.touch()
        p2.touch()
        return [p0, p1, p2, p3]

    @pytest.mark.parametrize(
        "cfn, env, expected",
        [
            ([], None, []),
            ([0], None, [0]),
            ([1], None, []),
            ([2], None, [2]),
            ([3], None, []),
            ([], [0], [0]),
            ([0, 1], [2, 3], [0, 2]),
            ([2, 1, 0], [2], [2, 0, 2]),
        ],
    )
    def test_get_config_filenames(
        self,
        cfn: List[int],
        env: Optional[List[int]],
        expected: List[int],
        fnames: List[Path],
        monkeypatch: MonkeyPatch,
    ):
        """
        Config files names (cfn) can be specified explicitly or via an env var.
        It's no problem if a files does not exist.
        """
        var: Optional[str]
        if env is not None:
            monkeypatch.setenv("CF", ":".join(str(fnames[i]) for i in env))
            var = "CF"
        else:
            var = None

        paths = FileLoader._get_config_filenames([fnames[i] for i in cfn], var)
        assert paths == [fnames[i] for i in expected]

    def test_get_config_filenames_empty_fn(
        self,
        fnames: List[Path],
        monkeypatch: MonkeyPatch,
    ):
        """
        Empty filenames from the env var are ignored.
        """
        monkeypatch.setenv("CF", f"::{fnames[0]}:")
        paths = FileLoader._get_config_filenames([], "CF")
        assert paths == fnames[:1]

    def test_load_file(self, tmp_path: Path):
        """
        Settings are cleaned for each file individually.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[le-section]
            le-option = "spam"
        """
        )

        @settings(frozen=True)
        class Settings:
            le_option: str = ""

        loader = FileLoader(
            formats={"*.toml": TomlFormat("le-section")},
            files=[config_file],
        )
        s = loader._load_file(config_file, Settings, _deep_options(Settings))
        assert s == {"le_option": "spam"}

    def test_load_file2(self, tmp_path: Path):
        """
        Settings are cleaned for each file individually.  In that process,
        "-" is normalized to "_".  This may result in duplicate settings and
        the last one wins in that case.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[le-section]
            le_option = "eggs"
            le-option = "spam"
        """
        )

        @settings(frozen=True)
        class Settings:
            le_option: str = ""

        loader = FileLoader(
            formats={"*.toml": TomlFormat("le-section")},
            files=[config_file],
        )
        s = loader._load_file(config_file, Settings, _deep_options(Settings))
        assert s == {"le_option": "spam"}

    def test_load_file_invalid_format(self):
        """
        An error is raised if a file has an unknown extension.
        """
        loader = FileLoader({"*.toml": TomlFormat("t")}, [])
        pytest.raises(
            UnknownFormatError, loader._load_file, Path("f.py"), [], type
        )

    def test_load(self, tmp_path: Path):
        """
        FileLoader() loads multiple files, each one overriding options
        from its predecessor.
        """
        cf1 = tmp_path.joinpath("s1.toml")
        cf1.write_text(
            """[le-section]
            le-spam = "spam"
            le-eggs = "spam"
        """
        )
        cf2 = tmp_path.joinpath("s2.toml")
        cf2.write_text(
            """[le-section]
            le_eggs = "eggs"
        """
        )

        @settings(frozen=True)
        class Settings:
            le_spam: str = ""
            le_eggs: str = ""

        loader = FileLoader({"*.toml": TomlFormat("le-section")}, [cf1, cf2])
        s = loader(Settings, _deep_options(Settings))
        assert s == {"le_spam": "spam", "le_eggs": "eggs"}

    @pytest.mark.parametrize(
        "is_mandatory, is_path, in_env, exists",
        product([True, False], repeat=4),
    )
    def test_mandatory_files(
        self,
        is_mandatory,
        is_path,
        in_env,
        exists,
        tmp_path,
        settings_cls: type,
        monkeypatch,
    ):
        """
        Paths with a "!" are mandatory and an error is raised if they don't
        exist.
        """
        p = tmp_path.joinpath("s.toml")
        if exists:
            p.touch()
        p = f"!{p}" if is_mandatory else str(p)
        if is_path:
            p = Path(p)
        files = []
        if in_env:
            monkeypatch.setenv("TEST_SETTINGS", str(p))
        else:
            files = [p]

        loader = FileLoader({"*": TomlFormat("test")}, files, "TEST_SETTINGS")
        if is_mandatory and not exists:
            pytest.raises(FileNotFoundError, loader, settings_cls, [])
        else:
            loader(settings_cls, [])


class TestEnvLoader:
    """Tests for EnvLoader"""

    def test_from_env(
        self, settings_cls: type, options: OptionList, monkeypatch: MonkeyPatch
    ):
        """
        Load options from env vars, ignore env vars for which no settings
        exist.
        """
        monkeypatch.setenv("T_URL", "foo")
        monkeypatch.setenv("T_HOST", "spam")  # Haha! Just a deceit!
        monkeypatch.setenv("T_HOST_PORT", "25")
        loader = EnvLoader(prefix="T_")
        results = loader(settings_cls, options)
        assert results == {
            "url": "foo",
            "host": {
                "port": "25",
            },
        }

    def test_no_env_prefix(
        self, settings_cls: type, options: OptionList, monkeypatch: MonkeyPatch
    ):
        """
        It is okay to use an empty prefix.
        """
        monkeypatch.setenv("URL", "spam")

        loader = EnvLoader(prefix="")
        results = loader(settings_cls, options)
        assert results == {"url": "spam"}


class TestInstanceLoader:
    """Tests for InstanceLoader"""

    def test_from_inst(
        self, settings_cls: type, options: OptionList, monkeypatch: MonkeyPatch
    ):
        """
        Load options from env vars, ignore env vars for which no settings
        exist.
        """
        # "Host" has the same attributes as the "Host" from conftest.py,
        # so it works (but only b/c it is a nested attribute and mypy doesn't
        # know what we are doing 🙈)
        inst = settings_cls(Host("spam", 42), "eggs", 23)
        loader = InstanceLoader(inst)
        results = loader(settings_cls, options)
        assert results == {
            "default": 23,
            "url": "eggs",
            "host": {
                "name": "spam",
                "port": 42,
            },
        }

    def test_invalid_type(
        self, settings_cls: type, options: OptionList, monkeypatch: MonkeyPatch
    ):
        """
        It is okay to use an empty prefix.
        """
        # "Settings" is not the same as "settings_cls" from conftest.py
        inst = Settings(Host("spam", 42), "eggs", 23)
        loader = InstanceLoader(inst)
        pytest.raises(ValueError, loader, settings_cls, options)
