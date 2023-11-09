"""
Tests for "typed_settings.cli.click".
"""
import unittest.mock as mock
from pathlib import Path
from typing import Any, Callable, Generic, List, Optional, TypeVar, Union

import attrs
import click
import click.testing
import pytest

import typed_settings.cli_click as cli_click
from typed_settings import (
    click_options,
    default_loaders,
    option,
    pass_settings,
    secret,
    settings,
)
from typed_settings.constants import METADATA_KEY
from typed_settings.types import SecretStr


T = TypeVar("T")


Invoke = Callable[..., click.testing.Result]


class CliResult(click.testing.Result, Generic[T]):
    """A container for the settings passed to a test CLI."""

    settings: Optional[T]


Cli = Callable[..., CliResult[T]]


@pytest.fixture(name="invoke")
def _invoke() -> Invoke:
    runner = click.testing.CliRunner()

    def invoke(cli: click.Command, *args: str) -> click.testing.Result:
        return runner.invoke(cli, args, catch_exceptions=False)

    return invoke


def test_simple_cli(invoke: Invoke) -> None:
    """
    Basic test "click_options()", create a simple CLI for simple settings.
    """

    @settings
    class Settings:
        o: int

    @click.command()
    @click_options(Settings, "test")
    def cli(settings: Settings) -> None:
        assert settings == Settings(3)

    invoke(cli, "--o=3")


def test_unkown_type(invoke: Invoke) -> None:
    """
    A TypeError is raised if the settings contain a type that the decorator
    cannot handle.
    """

    @settings
    class Settings:
        o: Union[int, str]

    with pytest.raises(
        TypeError,
        match=r"Cannot create CLI option for: typing.Union\[int, str\]",
    ):

        @click.command()  # pragma: no cover
        @click_options(Settings, "test")
        def cli(settings: Settings) -> None:
            ...


def test_attrs_meta_not_modified() -> None:
    """
    The attrs meta data with with user defined click config is not modified.

    Regression test for #29.
    """

    @settings
    class S:
        opt: int = option(help="spam", click={"callback": print})

    meta = attrs.fields(S).opt.metadata[METADATA_KEY]

    assert meta[cli_click.METADATA_KEY] == {"help": "spam", "callback": print}

    click_options(S, "test")(lambda s: None)  # pragma: no cover
    click_options(S, "test")(lambda s: None)  # pragma: no cover

    assert meta[cli_click.METADATA_KEY] == {"help": "spam", "callback": print}


class TestDefaultsLoading:
    """
    Tests for loading default values.
    """

    def test_no_default(self, invoke: Invoke, monkeypatch: pytest.MonkeyPatch) -> None:
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
        def cli(settings: Settings) -> None:
            ...

        result = invoke(cli)
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "Try 'cli --help' for help.\n"
            "\n"
            "Error: Missing option '--b'.\n"
        )
        assert result.exit_code == 2

    def test_help_text(self, invoke: Invoke) -> None:
        """
        cli_options/secrets can specify a help text for click cli_options.
        """

        @settings
        class Settings:
            a: str = option(default="spam", help="Help for 'a'")
            b: str = secret(default="eggs", help="bbb")

        @click.command()
        @click_options(Settings, default_loaders("test"))
        def cli(settings: Settings) -> None:
            ...

        result = invoke(cli, "--help")
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --a TEXT  Help for 'a'  [default: spam]\n"
            "  --b TEXT  bbb  [default: (*******)]\n"
            "  --help    Show this message and exit.\n"
        )
        assert result.exit_code == 0

    def test_help_text_secrets(self, invoke: Invoke) -> None:
        """
        Defaults for Secret(Str) type defaults are not show even if "option()"
        and not "secret()" is used.
        """

        @settings
        class Settings:
            a: SecretStr = SecretStr("spam")
            # b: Secret[int] = Secret(42)

        @click.command()
        @click_options(Settings, default_loaders("test"))
        def cli(settings: Settings) -> None:
            ...

        result = invoke(cli, "--help")
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --a TEXT  [default: (*******)]\n"
            "  --help    Show this message and exit.\n"
        )
        assert result.exit_code == 0

    def test_show_envvar_not_in_help(self, invoke: Invoke) -> None:
        """
        The env var will not be shown if the envloader is not being used.
        """

        @settings
        class Settings:
            a: str = "spam"
            b: str = secret(default="eggs")

        @click.command()
        @click_options(Settings, [], show_envvars_in_help=True)
        def cli(settings: Settings) -> None:
            ...

        result = invoke(cli, "--help")
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --a TEXT  [default: spam]\n"
            "  --b TEXT  [default: (*******)]\n"
            "  --help    Show this message and exit.\n"
        )
        assert result.exit_code == 0

    def test_long_name(self, invoke: Invoke) -> None:
        """
        Underscores in option names are replaces with "-" in Click cli_options.
        """

        @settings
        class Settings:
            long_name: str = "val"

        @click.command()
        @click_options(Settings, default_loaders("test"))
        def cli(settings: Settings) -> None:
            ...

        result = invoke(cli, "--help")
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --long-name TEXT  [default: val]\n"
            "  --help            Show this message and exit.\n"
        )
        assert result.exit_code == 0

    def test_click_default_from_settings(
        self, invoke: Invoke, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """
        If a setting is set in a config file, that value is being used as
        default for click cli_options - *not* the default defined in the
        Settings class.
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
            Settings,
            default_loaders("test", [tmp_path.joinpath("settings.toml")]),
        )
        def cli(settings: Settings) -> None:
            ...

        result = invoke(cli, "--help")
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

    def test_default_factory_multiple_invocation(self, invoke: Invoke) -> None:
        """
        Default factories are not invoked by click when the CLI is generated.
        They are evaluate during the "convert" phase each time the CLI is invoked.
        """
        loaded_settings: List["Settings"] = []

        @settings
        class Settings:
            o: int = option(factory=lambda: len(loaded_settings) + 1)

        @click.command()
        @click_options(Settings, "example")
        def cli(settings: Settings) -> None:
            loaded_settings.append(settings)

        invoke(cli)
        invoke(cli)
        invoke(cli, "--o=100")
        assert loaded_settings == [Settings(1), Settings(2), Settings(100)]


class TestSettingsPassing:
    """
    Test for passing settings as positional or keyword arg.
    """

    def test_pass_as_pos_arg(self, invoke: Invoke) -> None:
        """
        If no explicit argname is provided, the settings instance is passed
        as positional argument.
        """

        @settings
        class Settings:
            o: int

        @click.command()
        @click_options(Settings, "test")
        # We should to this in this test:
        #   def cli(settings: Settings, /) -> None:
        # but that does not work in py37, so we just use name that is
        # != CTX_KEY.
        def cli(s: Settings) -> None:
            assert s == Settings(3)

        invoke(cli, "--o=3")

    def test_pos_arg_order_1(self, invoke: Invoke) -> None:
        """
        The inner most decorator maps to the first argument.
        """

        @settings
        class Settings:
            o: int = 0

        @click.command()
        @click_options(Settings, "test")
        @click.pass_obj
        # def cli(obj: dict, settings: Settings, /) -> None:
        def cli(obj: dict, settings: Settings) -> None:
            assert settings == Settings(3)
            assert obj["settings"] is settings

        result = invoke(cli, "--o=3")
        assert result.exit_code == 0, result.output

    def test_pos_arg_order_2(self, invoke: Invoke) -> None:
        """
        The inner most decorator maps to the first argument.

        Variant of "test_pos_arg_order_1" with swapeed decorators/args.
        """

        @settings
        class Settings:
            o: int = 0

        @click.command()
        @click.pass_obj
        @click_options(Settings, "test")
        # def cli(settings: Settings, obj: dict, /) -> None:
        def cli(settings: Settings, obj: dict) -> None:
            assert settings == Settings(3)
            assert obj["settings"] is settings

        result = invoke(cli, "--o=3")
        assert result.exit_code == 0, result.output

    def test_change_arg_name(self, invoke: Invoke) -> None:
        """
        The name of the settings argument can be changed.  It is then passed
        as kwarg.
        """

        @settings
        class Settings:
            o: int

        @click.command()
        @click_options(Settings, "test", argname="le_settings")
        def cli(*, le_settings: Settings) -> None:
            assert le_settings == Settings(3)

        result = invoke(cli, "--o=3")
        assert result.exit_code == 0, result.output

    def test_multi_settings(self, invoke: Invoke) -> None:
        """
        Multiple settings classes can be used when the argname is changed.
        """

        @settings
        class A:
            a: int = 0

        @settings
        class B:
            b: str = "b"

        @click.command()
        @click_options(A, "test-a", argname="sa")
        @click_options(B, "test-b", argname="sb")
        def cli(*, sa: A, sb: B) -> None:
            assert sa == A()
            assert sb == B()
            print("ok")

        result = invoke(cli)
        assert result.output == "ok\n"

        result = invoke(cli, "--help")
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --a INTEGER  [default: 0]\n"
            "  --b TEXT     [default: b]\n"
            "  --help       Show this message and exit.\n"
        )

    def test_multi_settings_duplicates(self, invoke: Invoke) -> None:
        """
        Different settings classes should not define the same options!
        """

        @settings
        class A:
            a: int = 0

        @settings
        class B:
            a: str = 3  # type: ignore
            b: str = "b"

        @click.command()
        @click_options(A, "test-a", argname="sa")
        @click_options(B, "test-b", argname="sb")
        def cli(*, sa: A, sb: B) -> None:
            ...

        result = invoke(cli, "--help")
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --a INTEGER  [default: 0]\n"
            "  --a TEXT     [default: 3]\n"
            "  --b TEXT     [default: b]\n"
            "  --help       Show this message and exit.\n"
        )

    def test_empty_cls(self, invoke: Invoke) -> None:
        """
        Empty settings classes are no special case.
        """

        @settings
        class S:
            pass

        @click.command()
        @click_options(S, "test")
        def cli(settings: S) -> None:
            assert settings == S()

        invoke(cli)


class TestPassSettings:
    """Tests for pass_settings()."""

    @settings
    class Settings:  # noqa: D106
        opt: str = ""

    def test_pass_settings(self, invoke: Invoke) -> None:
        """
        A subcommand can receive the settings (as pos arg) via the
        `pass_settings` decorator.
        """

        @click.group()
        @click_options(self.Settings, default_loaders("test"))
        def cli(settings: TestPassSettings.Settings) -> None:
            pass

        @cli.command()
        @pass_settings
        def cmd(s: TestPassSettings.Settings) -> None:
            assert s == self.Settings(opt="spam")

        invoke(cli, "--opt=spam", "cmd")

    def test_change_argname(self, invoke: Invoke) -> None:
        """
        The argument name for "pass_settings" can be changed but must be the
        same as in "click_options()".
        """

        @click.group()
        @click_options(self.Settings, "test", argname="le_settings")
        def cli(le_settings: TestPassSettings.Settings) -> None:
            pass

        @cli.command()
        @pass_settings(argname="le_settings")
        def cmd(*, le_settings: TestPassSettings.Settings) -> None:
            assert le_settings == self.Settings(opt="spam")

        invoke(cli, "--opt=spam", "cmd")

    def test_pass_settings_no_settings(self, invoke: Invoke) -> None:
        """
        Pass ``None`` if no settings are defined.
        """

        @click.group()
        def cli() -> None:
            pass

        @cli.command()
        @pass_settings
        def cmd(settings: TestPassSettings.Settings) -> None:
            assert settings is None

        invoke(cli, "cmd")

    def test_change_argname_no_settings(self, invoke: Invoke) -> None:
        """
        Pass ``None`` if no settings are defined.
        """

        @click.group()
        def cli() -> None:
            pass

        @cli.command()
        @pass_settings(argname="le_settings")
        def cmd(le_settings: TestPassSettings.Settings) -> None:
            assert le_settings is None

        invoke(cli, "cmd")

    def test_pass_in_parent_context(self, invoke: Invoke) -> None:
        """
        The decorator can be used in the same context as "click_options()".
        This makes no sense, but works.
        Since the settings are passed as pos. args, the cli receives two
        instances in that case.
        """

        @click.command()
        @click_options(self.Settings, "test")
        @pass_settings
        def cli(s1: TestPassSettings.Settings, s2: TestPassSettings.Settings) -> None:
            assert s1 is s2

        invoke(cli, "--opt=spam")

    def test_pass_in_parent_context_argname(self, invoke: Invoke) -> None:
        """
        The decorator can be used in the same context as "click_options()".
        This makes no sense, but works.
        With an explicit argname, only one instance is passed.
        """

        @click.command()
        @click_options(self.Settings, "test", argname="le_settings")
        @pass_settings(argname="le_settings")
        def cli(*, le_settings: "TestPassSettings.Settings") -> None:
            assert le_settings == self.Settings("spam")

        invoke(cli, "--opt=spam")

    def test_combine_pass_settings_click_options(self, invoke: Invoke) -> None:
        """
        A sub command can receive the parent's options via "pass_settings"
        and define its own options at the same time.
        """

        @settings
        class SubSettings:
            sub: str = ""

        @click.group()
        @click_options(self.Settings, "test-main", argname="main")
        def cli(main: TestPassSettings.Settings) -> None:
            assert main == self.Settings("spam")

        @cli.command()
        @click_options(SubSettings, "test-sub", argname="sub")
        @pass_settings(argname="main")
        def cmd(main: TestPassSettings.Settings, sub: SubSettings) -> None:
            assert main == self.Settings("spam")
            assert sub == SubSettings("eggs")

        invoke(cli, "--opt=spam", "cmd", "--sub=eggs")


class TestClickConfig:
    """Tests for influencing the option declaration."""

    @pytest.mark.parametrize(
        "click_config",
        [None, {"param_decls": ("--opt/--no-opt",)}],
    )
    @pytest.mark.parametrize(
        "flag, value", [(None, True), ("--opt", True), ("--no-opt", False)]
    )
    def test_default_for_flag_has_on_and_off_switch(
        self,
        invoke: Invoke,
        click_config: Optional[dict],
        flag: Optional[str],
        value: bool,
    ) -> None:
        """
        The attrs default value is correctly used for flag options in all
        variants (no flag, on-flag, off-flag).
        """

        @settings
        class Settings:
            opt: bool = option(default=True, click=click_config)

        @click.command()
        @click_options(Settings, "test")
        def cli(settings: Settings) -> None:
            assert settings.opt is value

        if flag is None:
            result = invoke(cli)
        else:
            result = invoke(cli, flag)
        assert result.exit_code == 0

    @pytest.mark.parametrize(
        "flag, value", [(None, False), ("--opt", True), ("--no-opt", False)]
    )
    def test_create_a_flag_without_off_switch(
        self, invoke: Invoke, flag: Optional[str], value: bool
    ) -> None:
        """
        The "off"-flag for flag options can be removed.
        """
        click_config = {"param_decls": "--opt", "is_flag": True}

        @settings
        class Settings:
            opt: bool = option(default=False, click=click_config)

        @click.command()
        @click_options(Settings, "test")
        def cli(settings: Settings) -> None:
            assert settings.opt is value

        if flag is None:
            result = invoke(cli)
        else:
            result = invoke(cli, flag)

        if flag == "--no-opt":
            assert result.exit_code == 2
        else:
            assert result.exit_code == 0

    @pytest.mark.parametrize(
        "flag, value", [(None, False), ("-x", True), ("--exitfirst", True)]
    )
    def test_create_a_short_handle_for_a_flag(
        self, invoke: Invoke, flag: Optional[str], value: bool
    ) -> None:
        """
        Create a shorter handle for a command similar to pytest's -x.
        """
        click_config = {"param_decls": ("-x", "--exitfirst"), "is_flag": True}

        @settings
        class Settings:
            exitfirst: bool = option(default=False, click=click_config)

        @click.command()
        @click_options(Settings, "test")
        def cli(settings: Settings) -> None:
            assert settings.exitfirst is value

        if flag is None:
            result = invoke(cli)
        else:
            result = invoke(cli, flag)
        assert result.exit_code == 0

    @pytest.mark.parametrize("args, value", [([], False), (["--arg"], True)])
    def test_user_callback_is_executed(
        self, invoke: Invoke, args: List[str], value: bool
    ) -> None:
        """
        A user callback is only invoked if an argument was passed, but not if the
        default is used.
        """
        cb = mock.MagicMock(return_value=value)

        click_config = {"callback": cb}

        @settings
        class Settings:
            arg: bool = option(default=False, click=click_config)

        @click.command()
        @click_options(Settings, "test")
        def cli(settings: Settings) -> None:
            assert settings.arg is value

        result = invoke(cli, *args)
        assert result.exit_code == 0
        assert cb.call_count == int(bool(args))


class TestDecoratorFactory:
    """
    Tests for the decorator factory (e.g., for option groups).
    """

    @pytest.fixture
    def settings_cls(self) -> type:
        @settings
        class Nested1:
            """
            Docs for Nested1
            """  # noqa: D415

            a: int = 0

        @settings
        class Nested2:
            # Deliberately has no docstring!
            a: int = 0

        @settings
        class Settings:
            """
            Main docs
            """  # noqa: D415

            a: int = 0
            n1: Nested1 = Nested1()
            n2: Nested2 = Nested2()

        return Settings

    def test_click_option_factory(self, settings_cls: type, invoke: Invoke) -> None:
        """
        The ClickOptionFactory is the default.
        """

        @click.command()
        @click_options(settings_cls, "t")
        def cli1(settings: Any) -> None:
            ...

        @click.command()
        @click_options(
            settings_cls,
            "t",
            decorator_factory=cli_click.ClickOptionFactory(),
        )
        def cli2(settings: Any) -> None:
            ...

        r1 = invoke(cli1, "--help").output.splitlines()[1:]
        r2 = invoke(cli2, "--help").output.splitlines()[1:]
        assert r1 == r2

    def test_option_group_factory(self, settings_cls: type, invoke: Invoke) -> None:
        """
        Option groups can be created via the OptionGroupFactory.
        """

        @click.command()
        @click_options(
            settings_cls,
            "t",
            decorator_factory=cli_click.OptionGroupFactory(),
        )
        def cli(settings: Any) -> None:
            ...

        result = invoke(cli, "--help").output.splitlines()
        assert result == [
            "Usage: cli [OPTIONS]",
            "",
            "Options:",
            "  Main docs: ",
            "    --a INTEGER       [default: 0]",
            "  Docs for Nested1: ",
            "    --n1-a INTEGER    [default: 0]",
            "  Nested2 options: ",
            "    --n2-a INTEGER    [default: 0]",
            "  --help              Show this message and exit.",
        ]

    def test_not_installed(self, unimport: Callable[[str], None]) -> None:
        """
        The factory checks if click-option-group is installed.
        """
        unimport("click_option_group")
        with pytest.raises(ModuleNotFoundError):
            cli_click.OptionGroupFactory()


@pytest.mark.parametrize(
    "factory",
    [None, cli_click.ClickOptionFactory(), cli_click.OptionGroupFactory()],
)
def test_show_envvar_in_help(
    factory: Optional[cli_click.DecoratorFactory], invoke: Invoke
) -> None:
    """
    An option's help can optionally show the env var that will be loaded.
    """

    @settings
    class Settings:
        a: str = "spam"
        b: str = secret(default="eggs")

    @click.command()
    @click_options(
        Settings,
        default_loaders("test"),
        decorator_factory=factory,
        show_envvars_in_help=True,
    )
    def cli(settings: Settings) -> None:
        ...

    result = invoke(cli, "--help")
    if isinstance(factory, cli_click.OptionGroupFactory):
        print(result.output)
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  Settings options: \n"
            "    --a TEXT          [env var: TEST_A; default: spam]\n"
            "    --b TEXT          [env var: TEST_B; default: (*******)]\n"
            "  --help              Show this message and exit.\n"
        )
    else:
        assert result.output == (
            "Usage: cli [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  --a TEXT  [env var: TEST_A; default: spam]\n"
            "  --b TEXT  [env var: TEST_B; default: (*******)]\n"
            "  --help    Show this message and exit.\n"
        )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "factory",
    [None, cli_click.ClickOptionFactory(), cli_click.OptionGroupFactory()],
)
def test_click_no_load_envvar(
    factory: Optional[cli_click.DecoratorFactory],
    invoke: Invoke,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The "show_envvars_in_help" option does not cause Click to load settings
    from envvars.
    """
    tmp_path.joinpath("settings.toml").write_text('[test]\na = "x"\n')
    spath = tmp_path.joinpath("settings2.toml")
    spath.write_text('[test]\na = "spam"\n')
    monkeypatch.setenv("TEST_A", "onoes")

    @settings
    class Settings:
        a: str = "spam"

    # Reverse loaders so that env loader is used first and the file loader
    # is used last (and thus has priority)
    loaders = list(reversed(default_loaders("test", [spath])))

    @click.command()
    @click_options(
        Settings,
        loaders,
        decorator_factory=factory,
        show_envvars_in_help=True,
    )
    def cli(settings: Settings) -> None:
        print(settings.a)

    result = invoke(cli)
    # If click read from the envvar, the output would be "onoes"
    assert result.output == "spam\n"
    assert result.exit_code == 0


def test_resolve_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke: Invoke
) -> None:
    """
    Relative paths passed via the command line are resolved based on the user's CWD.
    """

    @settings
    class Settings:
        a: Path = Path("default")
        b: Path = Path("default")  # Load from file
        c: Path = Path("default")  # Load from env var
        d: Path = Path("default")  # Load from cli arg

    spath = tmp_path.joinpath("settings.toml")
    spath.write_text('[test]\nb = "file"\n')
    monkeypatch.setenv("TEST_C", "env")

    # chdir *before* creating the CLI, b/c it will load the defaults immediately:
    subdir = tmp_path.joinpath("sub")
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    result = Settings()  # Will be update by the CLI

    @click.command()
    @click_options(Settings, default_loaders("test", [spath]))
    def cli(settings: Settings) -> None:
        nonlocal result
        result = settings

    invoke(cli, "--d", "arg")
    assert result == Settings(
        a=subdir.joinpath("default"),
        b=spath.parent.joinpath("file"),
        c=subdir.joinpath("env"),
        d=subdir.joinpath("arg"),
    )


def test_multiple_invocations(invoke: Invoke) -> None:
    """
    A CLI function can be invoked multiple times w/o carrying state from call to call.
    """

    @settings
    class Settings:
        o: int = 0

    loaded_settings: List[Settings] = []

    @click.command()
    @click_options(Settings, "example")
    def cli(settings: Settings) -> None:
        loaded_settings.append(settings)

    # The order of these invocations is important:
    invoke(cli, "--o=3")
    invoke(cli)
    assert loaded_settings == [Settings(3), Settings(0)]
