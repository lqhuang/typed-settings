from pathlib import Path

from pytest import MonkeyPatch
import pytest

from typed_settings.loaders import EnvLoader, TomlFormat, FileLoader
from typed_settings.types import OptionList


class TestTomlFormat:
    """Tests for TomlFormat"""

    def test_load_toml(self, tmp_path: Path):
        """
        We can load settings from a TOML file.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[example]
            url = "spam"
            [example.host]
            port = 42
        """
        )
        result = TomlFormat().load_file(config_file, "example")
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
        result = TomlFormat().load_file(config_file, "tool.example")
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
        result = TomlFormat().load_file(config_file, section)
        assert result == {}


class TestFromToml:
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
        self, cfn, env, expected, fnames, monkeypatch
    ):
        """
        Config files names (cnf) can be specified explicitly or via an env var.
        It's no problem if a files does not exist (or is it?).
        """
        if env is not None:
            monkeypatch.setenv("CF", ":".join(str(fnames[i]) for i in env))
            env = "CF"

        paths = _core._get_config_filenames([fnames[i] for i in cfn], env)
        assert paths == [fnames[i] for i in expected]

    def test_load_convert_dashes(self, tmp_path):
        # TODO: move to test_clean-settings
        """
        Dashes in settings and section names are replaced with underscores.
        """

        @frozen
        class Sub:
            b_1: str

        @frozen
        class Settings:
            a_1: str
            a_2: str
            sub_section: Sub

        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[example]
            a-1 = "spam"
            a_2 = "eggs"
            [example.sub-section]
            b-1 = "bacon"
        """
        )
        results = _core._load_toml(
            _deep_options(Settings), config_file, "example"
        )
        assert results == {
            "a_1": "spam",
            "a_2": "eggs",
            "sub_section": {"b_1": "bacon"},
        }

    def test_invalid_settings(self):
        """
        Settings for which there is no attribute are errors
        """
        settings = {
            "url": "abc",
            "host": {"port": 23, "eggs": 42},
            "spam": 23,
        }
        with pytest.raises(ValueError) as exc_info:
            _core._clean_settings(_deep_options(Settings), settings, Path("p"))
        assert str(exc_info.value) == (
            "Invalid settings found in p: host.eggs, spam"
        )

    def test_clean_settings_unresolved_type(self):
        """
        Cleaning must also work if an options type is an unresolved string.
        """

        @frozen
        class Host:
            port: int = field(converter=int)

        @frozen
        class Settings:
            host: "Host"

        settings = {"host": {"port": 23, "eggs": 42}}
        with pytest.raises(ValueError) as exc_info:
            _core._clean_settings(_deep_options(Settings), settings, Path("p"))
        assert str(exc_info.value) == "Invalid settings found in p: host.eggs"

    def test_clean_settings_dict_values(self):
        """
        Some dicts may be actuall values (not nested) classes.  Don't try to
        check theses as option paths.
        """

        @frozen
        class Settings:
            option: Dict[str, Any]

        settings = {"option": {"a": 1, "b": 2}}
        _core._clean_settings(_deep_options(Settings), settings, Path("p"))

    def test_no_replace_dash_in_dict_keys(self, tmp_path):
        """
        "-" in TOML keys are replaced with "_" for sections and options, but
        "-" in actuall dict keys are left alone.

        See: https://gitlab.com/sscherfke/typed-settings/-/issues/3
        """

        @frozen
        class Settings:
            option_1: Dict[str, Any]
            option_2: Dict[str, Any]

        cf = tmp_path.joinpath("settings.toml")
        cf.write_text(
            "[my-config]\n"
            'option-1 = {my-key = "val1"}\n'
            "[my-config.option-2]\n"
            "another-key = 23\n"
        )

        settings = _core._load_toml(_deep_options(Settings), cf, "my-config")
        assert settings == {
            "option_1": {"my-key": "val1"},
            "option_2": {"another-key": 23},
        }

    def test_load_settings_explicit_config(self, tmp_path, monkeypatch):
        """
        The automatically derived config section name and settings files var
        name can be overriden.
        """
        config_file = tmp_path.joinpath("settings.toml")
        config_file.write_text(
            """[le-section]
            spam = "eggs"
        """
        )

        monkeypatch.setenv("LE_SETTINGS", str(config_file))

        @frozen
        class Settings:
            spam: str = ""

        settings = _core._from_toml(
            _deep_options(Settings),
            appname="example",
            files=[],
            section="le-section",
            var_name="LE_SETTINGS",
        )
        assert settings == {"spam": "eggs"}

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

        args = ([], "test", files, _core.AUTO, _core.AUTO)
        if is_mandatory and not exists:
            pytest.raises(FileNotFoundError, _core._from_toml, *args)
        else:
            _core._from_toml(*args)

    def test_env_var_dash_underscore(self, monkeypatch, tmp_path):
        """
        Dashes in the appname get replaced with underscores for the settings
        fiels var name.
        """

        @frozen
        class Settings:
            option: bool = True

        sf = tmp_path.joinpath("settings.py")
        sf.write_text("[a-b]\noption = false\n")
        monkeypatch.setenv("A_B_SETTINGS", str(sf))

        result = _core.load(Settings, appname="a-b")
        assert result == Settings(option=False)


class TestEnvLoader:
    """Tests for EnvLoader"""

    def test_from_env(self, options: OptionList, monkeypatch: MonkeyPatch):
        """
        Load options from env vars, ignore env vars for which no settings
        exist.
        """
        monkeypatch.setenv("T_URL", "foo")
        monkeypatch.setenv("T_HOST", "spam")  # Haha! Just a deceit!
        monkeypatch.setenv("T_HOST_PORT", "25")
        loader = EnvLoader(prefix="T_")
        settings = loader.load(options)
        assert settings == {
            "url": "foo",
            "host": {
                "port": "25",
            },
        }

    def test_no_env_prefix(
        self, options: OptionList, monkeypatch: MonkeyPatch
    ):
        """
        It is okay to use an empty prefix.
        """
        monkeypatch.setenv("URL", "spam")

        loader = EnvLoader(prefix="")
        settings = loader.load(options)
        assert settings == {"url": "spam"}
