from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    MutableSequence,
    MutableSet,
    Sequence,
    Set,
    Tuple,
)

import attr
import click
import click.testing
import pytest

from typed_settings import (
    click_options,
    click_utils,
    option,
    pass_settings,
    secret,
    settings,
)


def make_cli(settings_cls: type) -> Callable[..., Any]:
    """
    Returns a ``cli`` fixture that creates a Click command for the given
    settings class.

    The fixture returns a ``Callable[[Arg, ...], Result]``.  The :result is a
    :class:`click.testing.Result` with an additional ``settings`` attribute.
    This contains an instance of the passed settings class.

    """

    @pytest.fixture
    def cli(self, tmp_path):
        """
        Creates a click command for ``Settings`` and returns a functions that
        invokes a click test runner with the passed arguments.

        The result object will habe a ``settings`` attribute that holds the
        generated ``Settings`` instance for verification.

        """

        class Runner(click.testing.CliRunner):
            settings: object

            def invoke(self, *args, **kwargs):
                result = super().invoke(*args, **kwargs)
                try:
                    result.settings = self.settings
                except AttributeError:
                    result.settings = None
                return result

        runner = Runner()

        @click.group(invoke_without_command=True)
        @click_options(
            settings_cls, "test", [tmp_path.joinpath("settings.toml")]
        )
        def cli(settings):
            runner.settings = settings

        def run(*args, **kwargs):
            return runner.invoke(cli, args, **kwargs)

        return run

    return cli


@pytest.mark.parametrize(
    "default, path, settings, expected",
    [
        (attr.NOTHING, "a", {"a": 3}, 3),
        (attr.NOTHING, "a", {}, attr.NOTHING),
        (2, "a", {}, 2),
        (attr.Factory(list), "a", {}, []),
    ],
)
def test_get_default(default, path, settings, expected):
    field = attr.Attribute("test", default, None, None, None, None, None, None)
    result = click_utils._get_default(field, path, settings)
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
    result = click_utils._get_default(field, "a", {})
    assert result == "eggs"


def test_no_default(monkeypatch):
    """
    Options without a default are mandatory/required.
    """

    @settings
    class S:
        a: str
        b: str

    monkeypatch.setenv("TEST_A", "spam")  # This makes only "S.b" mandatory!

    @click.command()
    @click_options(S, "test")
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
    Options/secrets can specify a help text for click options.
    """

    @settings
    class S:
        a: str = option(default="spam", help="Help for 'a'")
        b: str = secret(default="eggs", help="bbb")

    @click.command()
    @click_options(S, "test")
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
    Underscores in option names are replaces with "-" in Click options.
    """

    @settings
    class S:
        long_name: str = "val"

    @click.command()
    @click_options(S, "test")
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
    for click options - *not* the default defined in the Settings class.
    """

    tmp_path.joinpath("settings.toml").write_text('[test]\na = "x"\n')
    spath = tmp_path.joinpath("settings2.toml")
    print(spath)
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
    @click_options(Settings, "test", [tmp_path.joinpath("settings.toml")])
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
    class S:
        opt: Dict[int, int]

    with pytest.raises(TypeError, match="Cannot create click type"):

        @click.command()
        @click_options(S, "test")
        def cli(settings):
            pass


class ClickTestBase:
    """
    Base class for Click tests.

    Each test must define a ``cli`` fixture.  That CLI is invoked three times:

    - With "--help", the result is compared to :attr:`_help`.
    - Without arguments, the result is compared to :attr:`_defaults`.
    - With arguments defined in :attr:`_options`, the result is compared to
      :attr:`_values`.
    """

    _help: List[str] = []
    _default_options: List[str] = []
    _defaults: Any = None
    _options: List[str] = []
    _values: Any = None

    def test_help(self, cli):
        """
        The genereated CLI has a proper help output.
        """
        result = cli("--help")

        # fmt: off
        assert result.output.splitlines()[:-1] == [
            "Usage: cli [OPTIONS] COMMAND [ARGS]...",
            "",
            "Options:",
        ] + self._help
        assert result.exit_code == 0
        # fmt: on

    def test_defaults(self, cli):
        """
        Arguments of the generated CLI have default values.
        """
        result = cli(*self._default_options)
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == self._defaults

    def test_options(self, cli):
        """
        Default values can be overriden by passing the corresponding args.
        """
        result = cli(*self._options)
        assert result.output == ""
        assert result.exit_code == 0
        assert result.settings == self._values


class TestClickBool(ClickTestBase):
    """
    Test boolean flags.
    """

    @settings
    class S:
        a: bool
        b: bool = True
        c: bool = False

    cli = make_cli(S)

    _help = [
        "  --a / --no-a  [default: no-a;required]",
        "  --b / --no-b  [default: b]",
        "  --c / --no-c  [default: no-c]",
    ]
    _defaults = S(False, True, False)
    _options = ["--no-a", "--no-b", "--c"]
    _values = S(False, False, True)


class TestIntFloatStr(ClickTestBase):
    """
    Test int, float and str options.
    """

    @settings
    class S:
        a: str = option(default="spam")
        b: str = secret(default="spam")
        c: int = 0
        d: float = 0

    cli = make_cli(S)

    _help = [
        "  --a TEXT     [default: spam]",
        "  --b TEXT     [default: ***]",
        "  --c INTEGER  [default: 0]",
        "  --d FLOAT    [default: 0.0]",
    ]
    _defaults = S()
    _options = ["--a=eggs", "--b=pwd", "--c=3", "--d=3.1"]
    _values = S(a="eggs", b="pwd", c=3, d=3.1)


class TestDateTime(ClickTestBase):
    """
    Test datetime options.
    """

    @settings
    class S:
        a: datetime = datetime.fromtimestamp(0, timezone.utc)
        b: datetime = datetime.fromtimestamp(0, timezone.utc)
        c: datetime = datetime.fromtimestamp(0, timezone.utc)

    cli = make_cli(S)

    _help = [
        "  --a [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 1970-01-01 00:00:00+00:00]",  # noqa: E501
        "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 1970-01-01 00:00:00+00:00]",  # noqa: E501
        "  --c [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 1970-01-01 00:00:00+00:00]",  # noqa: E501
    ]
    _defaults = S()
    _options = [
        "--a=2020-05-04",
        "--b=2020-05-04T13:37:00",
        "--c=2020-05-04T13:37:00+00:00",
    ]
    _values = S(
        datetime(2020, 5, 4),
        datetime(2020, 5, 4, 13, 37),
        datetime(2020, 5, 4, 13, 37, tzinfo=timezone.utc),
    )


class LeEnum(Enum):
    spam = "le spam"
    eggs = "Le eggs"


class TestEnum(ClickTestBase):
    """
    Test enum options
    """

    @settings
    class S:
        a: LeEnum
        b: LeEnum = LeEnum.spam

    cli = make_cli(S)

    _help = [
        "  --a [spam|eggs]  [required]",
        "  --b [spam|eggs]  [default: spam]",
    ]
    _default_options = ["--a=spam"]
    _defaults = S(a=LeEnum.spam)
    _options = ["--a=spam", "--b=eggs"]
    _values = S(LeEnum.spam, LeEnum.eggs)


class TestPath(ClickTestBase):
    """
    Test Path options
    """

    @settings
    class S:
        a: Path = Path("/")

    cli = make_cli(S)

    _help = ["  --a PATH  [default: /]"]
    _defaults = S()
    _options = ["--a=/spam"]
    _values = S(Path("/spam"))


class TestNested(ClickTestBase):
    """
    Test options for nested settings
    """

    @settings
    class S:
        @settings
        class Nested:
            a: str = "nested"
            b: int = 0

        n: Nested = Nested()

    cli = make_cli(S)

    _help = [
        "  --n-a TEXT     [default: nested]",
        "  --n-b INTEGER  [default: 0]",
    ]
    _defaults = S()
    _options = ["--n-a=eggs", "--n-b=3"]
    _values = S(S.Nested("eggs", 3))


class TestList(ClickTestBase):
    """
    Lists (and friends) use "multiple=True".
    """

    @settings
    class S:
        a: List[int]
        b: Sequence[datetime] = [datetime(2020, 5, 4)]
        c: MutableSequence[int] = []
        d: Set[int] = set()
        e: MutableSet[int] = set()
        f: FrozenSet[int] = frozenset()

    cli = make_cli(S)

    _help = [
        "  --a INTEGER                     [default: ;required]",
        "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 2020-05-04 00:00:00]",
        "  --c INTEGER                     [default: ]",
        "  --d INTEGER                     [default: ]",
        "  --e INTEGER                     [default: ]",
        "  --f INTEGER                     [default: ]",
    ]
    _default_options = ["--a=1"]
    _defaults = S(a=[1])
    _options = [
        "--a=1",
        "--a=2",
        "--b=2020-01-01",
        "--b=2020-01-02",
        "--c=3",
        "--d=4",
        "--e=5",
        "--f=6",
    ]
    _values = S(
        [1, 2],
        [datetime(2020, 1, 1), datetime(2020, 1, 2)],
        [3],
        {4},
        {5},
        frozenset({6}),
    )


class TestTuple(ClickTestBase):
    """
    Tuples are handled either like the list variant with multiple=True or
    like the struct variant with nargs=x.
    """

    @settings
    class S:
        a: Tuple[int, ...] = (0,)
        b: Tuple[int, float, str] = (0, 0.0, "")

    cli = make_cli(S)

    _help = [
        "  --a INTEGER                  [default: 0]",
        "  --b <INTEGER FLOAT TEXT>...  [default: 0, 0.0, ]",
    ]
    _defaults = S()
    _options = ["--a=1", "--a=2", "--b", "1", "2.3", "spam"]
    _values = S((1, 2), (1, 2.3, "spam"))


class TestNestedTuple(ClickTestBase):
    """
    Lists of tuples use "multiple=True" and "nargs=x".
    """

    @settings
    class S:
        a: List[Tuple[int, int]] = option(factory=list)

    cli = make_cli(S)

    _help = [
        "  --a <INTEGER INTEGER>...  [default: ]",
    ]
    _defaults = S()
    _options = ["--a", "1", "2", "--a", "3", "4"]
    _values = S([(1, 2), (3, 4)])


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
        @click_options(self.Settings, "test")
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
        @click_options(self.Settings, "test")
        @pass_settings
        def cli(s1, s2):
            click.echo(s1 == s2)

        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["--opt=spam"])
        assert result.output == "True\n"
        assert result.exit_code == 0
