from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Generic,
    List,
    MutableSequence,
    MutableSet,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
)

import attr
import click
import click.testing
import pytest
from _pytest.python import Metafunc

from typed_settings import (
    click_options,
    click_utils,
    default_converter,
    default_loaders,
    option,
    pass_settings,
    secret,
    settings,
)


T = TypeVar("T")


class CliResult(click.testing.Result, Generic[T]):
    settings: Optional[T]


Cli = Callable[..., CliResult[T]]


def make_cli(settings_cls: Type[T]) -> Cli:
    """
    Return a function that invokes a Click CLI with Typed Settings options
    for *settings_cls*.

    That functions returns a :class:`CliResult` with the loaded settings
    instance (:attr:`CliResult.settings`).
    """

    class Runner(click.testing.CliRunner):
        settings: Optional[T]

        def invoke(self, *args, **kwargs) -> CliResult:
            result = super().invoke(*args, **kwargs)
            cli_result: CliResult[T] = CliResult(**result.__dict__)
            try:
                cli_result.settings = self.settings
            except AttributeError:
                cli_result.settings = None
            return cli_result

    runner = Runner()

    def run(*args, **kwargs) -> CliResult:
        @click.group(invoke_without_command=True)
        @click_options(settings_cls, default_loaders("test"))
        def cli(settings: T) -> None:
            runner.settings = settings

        return runner.invoke(cli, args, **kwargs)

    return run


def test_simple_cli():
    """
    "click_options()" uses the default loaders if you just pass an app name.
    """

    @settings
    class Settings:
        o: int

    loaded = []

    @click.command()
    @click_options(Settings, "test")
    def cli(settings: Settings) -> None:
        loaded.append(settings)

    result = click.testing.CliRunner().invoke(cli, ["--o=3"])
    assert result.exit_code == 0
    assert loaded == [Settings(3)]


@pytest.mark.parametrize(
    "default, path, type, settings, expected",
    [
        (attr.NOTHING, "a", int, {"a": 3}, 3),
        (attr.NOTHING, "a", int, {}, attr.NOTHING),
        (2, "a", int, {}, 2),
        (attr.Factory(list), "a", List[int], {}, []),
    ],
)
def test_get_default(default, path, type, settings, expected):
    converter = default_converter()
    field = attr.Attribute(
        "test", default, None, None, None, None, None, None, type=type
    )
    result = click_utils._get_default(field, path, settings, converter)
    assert result == expected


def test_get_default_factory():
    """
    If the factory "takes self", ``None`` is passed since we do not yet have
    an instance.
    """

    def factory(self) -> str:
        assert self is None
        return "eggs"

    default = attr.Factory(factory, takes_self=True)
    field = attr.Attribute("test", default, None, None, None, None, None, None)
    result = click_utils._get_default(field, "a", {}, default_converter())
    assert result == "eggs"


def test_no_default(monkeypatch):
    """
    cli_options without a default are mandatory/required.
    """

    @settings
    class Settings:
        a: str
        b: str

    monkeypatch.setenv("TEST_A", "spam")  # This makes only "S.b" mandatory!

    @click.command()
    @click_options(Settings, default_loaders("test"))
    def cli(settings):
        pass

    runner = click.testing.CliRunner()
    result = runner.invoke(cli, [])
    assert result.output == (
        "Usage: cli [OPTIONS]\n"
        "Try 'cli --help' for help.\n"
        "\n"
        "Error: Missing option '--b'.\n"
    )
    assert result.exit_code == 2


def test_help_text():
    """
    cli_options/secrets can specify a help text for click cli_options.
    """

    @settings
    class Settings:
        a: str = option(default="spam", help="Help for 'a'")
        b: str = secret(default="eggs", help="bbb")

    @click.command()
    @click_options(Settings, default_loaders("test"))
    def cli(settings):
        pass

    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.output == (
        "Usage: cli [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  --a TEXT  Help for 'a'  [default: spam]\n"
        "  --b TEXT  bbb  [default: ***]\n"
        "  --help    Show this message and exit.\n"
    )
    assert result.exit_code == 0


def test_long_name():
    """
    Underscores in option names are replaces with "-" in Click cli_options.
    """

    @settings
    class Settings:
        long_name: str = "val"

    @click.command()
    @click_options(Settings, default_loaders("test"))
    def cli(settings):
        pass

    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.output == (
        "Usage: cli [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  --long-name TEXT  [default: val]\n"
        "  --help            Show this message and exit.\n"
    )
    assert result.exit_code == 0


def test_click_default_from_settings(monkeypatch, tmp_path):
    """
    If a setting is set in a config file, that value is being used as default
    for click cli_options - *not* the default defined in the Settings class.
    """

    tmp_path.joinpath("settings.toml").write_text('[test]\na = "x"\n')
    spath = tmp_path.joinpath("settings2.toml")
    spath.write_text('[test]\nb = "y"\n')
    monkeypatch.setenv("TEST_SETTINGS", str(spath))
    monkeypatch.setenv("TEST_C", "z")

    @settings
    class Settings:
        a: str
        b: str
        c: str
        d: str

    @click.command()
    @click_options(
        Settings, default_loaders("test", [tmp_path.joinpath("settings.toml")])
    )
    def cli(settings):
        print(settings)

    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.output == (
        "Usage: cli [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  --a TEXT  [default: x]\n"
        "  --b TEXT  [default: y]\n"
        "  --c TEXT  [default: z]\n"
        "  --d TEXT  [required]\n"
        "  --help    Show this message and exit.\n"
    )
    assert result.exit_code == 0


def test_unsupported_generic():
    @settings
    class Settings:
        opt: Dict[int, int]

    with pytest.raises(TypeError, match="Cannot create click type"):

        @click.command()
        @click_options(Settings, default_loaders("test"))
        def cli(settings):
            pass


class LeEnum(Enum):
    spam = "Le spam"
    eggs = "Le eggs"


class TestClickParamTypes:
    """
    Test the behavior of click options for various parameter types.

    """

    class ClickParamBase:
        """
        Base class for test parameters.

        Sublcasses must define:

        - A settings class
        - A list of expected "--help" outputs for each option
        - Optionally, required arguments for options with no default.
        - An instance of the settings class with expected default option
          values.
        - A list of Cli options and the expected settings result.
        """

        @settings
        class Settings:
            pass

        expected_help: List[str] = []

        env_vars: Dict[str, str] = {}
        expected_env_var_defaults: List[str] = []

        default_options: List[str] = []
        expected_defaults: Any = None

        cli_options: List[str] = []
        expected_settings: Any = None

        _classes: List["TestClickParamTypes.ClickParamBase"] = []

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            cls._classes.append(cls)

    class ClickBoolParam(ClickParamBase):
        """
        Test boolean flags.
        """

        @settings
        class Settings:
            a: bool
            b: bool = True
            c: bool = False

        expected_help = [
            "  --a / --no-a  [required]",
            "  --b / --no-b  [default: b]",
            "  --c / --no-c  [default: no-c]",
        ]

        env_vars = {"A": "1", "B": "0"}
        expected_env_var_defaults = [
            "  --a / --no-a  [default: a]",
            "  --b / --no-b  [default: no-b]",
            "  --c / --no-c  [default: no-c]",
        ]

        default_options = ["--a"]
        expected_defaults = Settings(True, True, False)

        cli_options = ["--no-a", "--no-b", "--c"]
        expected_settings = Settings(False, False, True)

    class IntFloatStrParam(ClickParamBase):
        """
        Test int, float and str cli_options.
        """

        @settings
        class Settings:
            a: str = option(default="spam")
            b: str = secret(default="spam")
            c: int = 0
            d: float = 0

        expected_help = [
            "  --a TEXT     [default: spam]",
            "  --b TEXT     [default: ***]",
            "  --c INTEGER  [default: 0]",
            "  --d FLOAT    [default: 0.0]",
        ]

        env_vars = {"A": "eggs", "B": "bacon", "C": "42", "D": "3.14"}
        expected_env_var_defaults = [
            "  --a TEXT     [default: eggs]",
            "  --b TEXT     [default: ***]",
            "  --c INTEGER  [default: 42]",
            "  --d FLOAT    [default: 3.14]",
        ]

        expected_defaults = Settings()

        cli_options = ["--a=eggs", "--b=pwd", "--c=3", "--d=3.1"]
        expected_settings = Settings(a="eggs", b="pwd", c=3, d=3.1)

    class DateTimeParam(ClickParamBase):
        """
        Test datetime cli_options.
        """

        @settings
        class Settings:
            a: datetime = datetime.fromtimestamp(0, timezone.utc)
            b: datetime = datetime.fromtimestamp(0, timezone.utc)
            c: datetime = datetime.fromtimestamp(0, timezone.utc)

        expected_help = [
            "  --a [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 1970-01-01T00:00:00+00:00]",  # noqa: E501
            "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 1970-01-01T00:00:00+00:00]",  # noqa: E501
            "  --c [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 1970-01-01T00:00:00+00:00]",  # noqa: E501
        ]

        env_vars = {
            "A": "2021-05-04T13:37:00Z",
            "B": "2021-05-04T13:37:00",
            "C": "2021-05-04",
        }
        expected_env_var_defaults = [
            "  --a [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 2021-05-04T13:37:00+00:00]",  # noqa: E501
            "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 2021-05-04T13:37:00]",  # noqa: E501
            "  --c [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 2021-05-04T00:00:00]",  # noqa: E501
        ]

        expected_defaults = Settings()

        cli_options = [
            "--a=2020-05-04",
            "--b=2020-05-04T13:37:00",
            "--c=2020-05-04T13:37:00+00:00",
        ]
        expected_settings = Settings(
            datetime(2020, 5, 4),
            datetime(2020, 5, 4, 13, 37),
            datetime(2020, 5, 4, 13, 37, tzinfo=timezone.utc),
        )

    class EnumParam(ClickParamBase):
        """
        Test enum cli_options
        """

        @settings
        class Settings:
            a: LeEnum
            b: LeEnum = LeEnum.spam

        expected_help = [
            "  --a [spam|eggs]  [required]",
            "  --b [spam|eggs]  [default: spam]",
        ]

        env_vars = {"A": "spam", "B": "eggs"}
        expected_env_var_defaults = [
            "  --a [spam|eggs]  [default: spam]",
            "  --b [spam|eggs]  [default: eggs]",
        ]

        default_options = ["--a=spam"]
        expected_defaults = Settings(a=LeEnum.spam)

        cli_options = ["--a=spam", "--b=eggs"]
        expected_settings = Settings(LeEnum.spam, LeEnum.eggs)

    class PathParam(ClickParamBase):
        """
        Test Path cli_options
        """

        @settings
        class Settings:
            a: Path = Path("/")

        expected_help = ["  --a PATH  [default: /]"]

        env_vars = {"A": "/spam/eggs"}
        expected_env_var_defaults = ["  --a PATH  [default: /spam/eggs]"]

        expected_defaults = Settings()

        cli_options = ["--a=/spam"]
        expected_settings = Settings(Path("/spam"))

    class NestedParam(ClickParamBase):
        """
        Test cli_options for nested settings
        """

        @settings
        class Settings:
            @settings
            class Nested:
                a: str = "nested"
                b: int = 0

            n: Nested = Nested()

        expected_help = [
            "  --n-a TEXT     [default: nested]",
            "  --n-b INTEGER  [default: 0]",
        ]

        env_vars = {"N_A": "spam", "N_B": "42"}
        expected_env_var_defaults = [
            "  --n-a TEXT     [default: spam]",
            "  --n-b INTEGER  [default: 42]",
        ]

        expected_defaults = Settings()

        cli_options = ["--n-a=eggs", "--n-b=3"]
        expected_settings = Settings(Settings.Nested("eggs", 3))

    class ListParam(ClickParamBase):
        """
        Lists (and friends) use "multiple=True".
        """

        @settings
        class Settings:
            a: List[int]
            b: Sequence[datetime] = [datetime(2020, 5, 4)]
            c: MutableSequence[int] = []
            d: Set[int] = set()
            e: MutableSet[int] = set()
            f: FrozenSet[int] = frozenset()

        expected_help = [
            "  --a INTEGER                     [required]",
            "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 2020-05-04T00:00:00]",
            "  --c INTEGER",
            "  --d INTEGER",
            "  --e INTEGER",
            "  --f INTEGER",
        ]

        env_vars = {
            "A": "1:2",
            "B": "2021-01-01:2021-01-02",  # Dates with times wont work here!
        }
        expected_env_var_defaults = [
            "  --a INTEGER                     [default: 1, 2]",
            "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
            "                                  [default: 2021-01-01T00:00:00,",
            "                                  2021-01-02T00:00:00]",
            "  --c INTEGER",
            "  --d INTEGER",
            "  --e INTEGER",
            "  --f INTEGER",
        ]

        default_options = ["--a=1"]
        expected_defaults = Settings(a=[1])

        cli_options = [
            "--a=1",
            "--a=2",
            "--b=2020-01-01",
            "--b=2020-01-02",
            "--c=3",
            "--d=4",
            "--e=5",
            "--f=6",
        ]
        expected_settings = Settings(
            [1, 2],
            [datetime(2020, 1, 1), datetime(2020, 1, 2)],
            [3],
            {4},
            {5},
            frozenset({6}),
        )

    class TupleParam(ClickParamBase):
        """
        Tuples are handled either like the list variant with multiple=True or
        like the struct variant with nargs=x.
        """

        @settings
        class Settings:
            a: Tuple[int, ...] = (0,)
            b: Tuple[int, float, str] = (0, 0.0, "")

        expected_help = [
            "  --a INTEGER                  [default: 0]",
            "  --b <INTEGER FLOAT TEXT>...  [default: 0, 0.0, ]",
        ]

        env_vars = {"A": "1:2", "B": "42:3.14:spam"}
        expected_env_var_defaults = [
            "  --a INTEGER                  [default: 1, 2]",
            "  --b <INTEGER FLOAT TEXT>...  [default: 42, 3.14, spam]",
        ]

        expected_defaults = Settings()

        cli_options = ["--a=1", "--a=2", "--b", "1", "2.3", "spam"]
        expected_settings = Settings((1, 2), (1, 2.3, "spam"))

    class NestedTupleParam(ClickParamBase):
        """
        Lists of tuples use "multiple=True" and "nargs=x".
        """

        @settings
        class Settings:
            a: List[Tuple[int, int]] = option(factory=list)

        expected_help = [
            "  --a <INTEGER INTEGER>...",
        ]

        # A list of tuples cannot be loaded with the default converter,
        # so we skip this test here.
        env_vars: Dict[str, Any] = {}
        expected_env_var_defaults = [
            "  --a <INTEGER INTEGER>...",
        ]

        expected_defaults = Settings()

        cli_options = ["--a", "1", "2", "--a", "3", "4"]
        expected_settings = Settings([(1, 2), (3, 4)])

    def pytest_generate_tests(self, metafunc: Metafunc) -> None:
        params = []
        fixtures = ["cli"] + [
            n for n in metafunc.fixturenames if hasattr(self.ClickParamBase, n)
        ]
        for param_cls in self.ClickParamBase._classes:
            argvals = []
            for name in fixtures:
                if name == "cli":
                    argvals.append(make_cli(param_cls.Settings))
                else:
                    argvals.append(getattr(param_cls, name))
            params.append(pytest.param(*argvals, id=param_cls.__name__))  # type: ignore  # noqa: E501

        metafunc.parametrize(fixtures, params)

    def test_help(self, cli: Cli[T], expected_help: List[str]):
        """
        The genereated CLI has a proper help output.
        """
        result = cli("--help")

        # fmt: off
        assert result.output.splitlines()[:-1] == [
            "Usage: cli [OPTIONS] COMMAND [ARGS]...",
            "",
            "Options:",
        ] + expected_help
        assert result.exit_code == 0
        # fmt: on

    def test_defaults_from_envvars(
        self,
        cli: Cli[T],
        env_vars: Dict[str, str],
        expected_env_var_defaults: List[str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """
        Previously loaded settings (e.g., from env vars) can be converted
        to click options.

        Regression test for #11
        """
        for var, val in env_vars.items():
            monkeypatch.setenv(f"TEST_{var}", val)

        result = cli("--help")

        # fmt: off
        assert result.output.splitlines()[:-1] == [
            "Usage: cli [OPTIONS] COMMAND [ARGS]...",
            "",
            "Options:",
        ] + expected_env_var_defaults
        assert result.exit_code == 0
        # fmt: on

    def test_defaults(
        self, cli: Cli[T], default_options: List[str], expected_defaults: T
    ):
        """
        Arguments of the generated CLI have default values.
        """
        result = cli(*default_options)
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == expected_defaults

    def test_options(
        self, cli: Cli[T], cli_options: List[str], expected_settings: T
    ):
        """
        Default values can be overriden by passing the corresponding args.
        """
        result = cli(*cli_options)
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == expected_settings


class TestPassSettings:
    """Tests for pass_settings()."""

    @settings
    class Settings:
        opt: str = ""

    def test_pass_settings(self):
        """
        A subcommand can receive the settings via the `pass_settings`
        decorator.
        """

        @click.group()
        @click_options(self.Settings, default_loaders("test"))
        def cli(settings):
            pass

        @cli.command()
        @pass_settings
        def cmd(settings):
            print(settings)
            assert settings == self.Settings(opt="spam")

        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["--opt=spam", "cmd"])
        assert result.output == "TestPassSettings.Settings(opt='spam')\n"
        assert result.exit_code == 0

    def test_pass_settings_no_settings(self):
        """
        Pass ``None`` if no settings are defined.
        """

        @click.group()
        def cli():
            pass

        @cli.command()
        @pass_settings
        def cmd(settings):
            print(settings)
            assert settings is None

        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["cmd"])
        assert result.output == "None\n"
        assert result.exit_code == 0

    def test_pass_in_parent_context(self):
        """
        The decorator can be used in the same context as "click_options()".
        This makes no sense, but works.
        """

        @click.command()
        @click_options(self.Settings, default_loaders("test"))
        @pass_settings
        def cli(s1, s2):
            click.echo(s1 == s2)

        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["--opt=spam"])
        assert result.output == "True\n"
        assert result.exit_code == 0
