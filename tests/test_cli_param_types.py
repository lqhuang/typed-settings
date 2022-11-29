import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
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
    Union,
)

import click
import click.testing
import pytest

from typed_settings import (
    argparse_utils,
    click_options,
    default_loaders,
    option,
    secret,
    settings,
)
from typed_settings.types import ST


class CliResult(click.testing.Result, Generic[ST]):
    settings: Optional[ST]


Cli = Callable[..., CliResult[ST]]
ArgParser = Callable[..., ST]


def make_cli(settings_cls: Type[ST]) -> Cli:
    """
    Return a function that invokes a Click CLI with Typed Settings options
    for *settings_cls*.

    That functions returns a :class:`CliResult` with the loaded settings
    instance (:attrs:`CliResult.settings`).
    """

    class Runner(click.testing.CliRunner):
        settings: Optional[ST]

        def invoke(self, *args, **kwargs) -> CliResult:
            result = super().invoke(*args, **kwargs)
            cli_result: CliResult[ST] = CliResult(**result.__dict__)
            try:
                cli_result.settings = self.settings
            except AttributeError:
                cli_result.settings = None
            return cli_result

    runner = Runner()

    def run(*args, **kwargs) -> CliResult:
        @click.group(invoke_without_command=True)
        @click_options(settings_cls, default_loaders("test"))
        def cli(settings: ST) -> None:
            runner.settings = settings

        result = runner.invoke(cli, args, catch_exceptions=False, **kwargs)
        assert result.exit_code == 0
        return result

    return run


def make_argparser(settings_cls: Type[ST]) -> ArgParser:
    def parse_args(*args: str) -> ST:
        parser = argparse_utils.make_parser(
            settings_cls, default_loaders("test")
        )
        namespace = parser.parse_args(args)
        return argparse_utils.namespace2settings(settings_cls, namespace)

    return parse_args


class LeEnum(Enum):
    spam = "Le spam"
    eggs = "Le eggs"


class ParamBase:
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

    classes: ClassVar[List["ParamBase"]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.classes.append(cls)

    @classmethod
    def get_expected_help(cls, prefix: str) -> List[str]:
        return getattr(cls, f"{prefix}_expected_help", cls.expected_help)

    @classmethod
    def get_expected_env_var_defaults(cls, prefix: str) -> List[str]:
        return getattr(
            cls,
            f"{prefix}_expected_env_var_defaults",
            cls.expected_env_var_defaults,
        )


class TestBoolParam(ParamBase):
    """
    Test boolean flags.
    """

    @settings(kw_only=True)
    class Settings:
        a: bool
        b: bool = True
        c: bool = False
        d: Optional[bool]
        e: Optional[bool] = None

    click_expected_help = [
        "  --a / --no-a  [required]",
        "  --b / --no-b  [default: b]",
        "  --c / --no-c  [default: no-c]",
        "  --d / --no-d",
        "  --e / --no-e",
    ]
    argparse_expected_help = [
        "  --a, --no-a  [required]",
        "  --b, --no-b  [default: True]",
        "  --c, --no-c  [default: False]",
        "  --d, --no-d",
        "  --e, --no-e",
    ]

    env_vars = {"A": "1", "B": "0"}
    click_expected_env_var_defaults = [
        "  --a / --no-a  [default: a]",
        "  --b / --no-b  [default: no-b]",
        "  --c / --no-c  [default: no-c]",
        "  --d / --no-d",
        "  --e / --no-e",
    ]
    argparse_expected_env_var_defaults = [
        "  --a, --no-a  [default: True]",
        "  --b, --no-b  [default: False]",
        "  --c, --no-c  [default: False]",
        "  --d, --no-d",
        "  --e, --no-e",
    ]

    default_options = ["--a"]
    expected_defaults = Settings(a=True, b=True, c=False, d=None, e=None)

    cli_options = ["--no-a", "--no-b", "--c"]
    expected_settings = Settings(a=False, b=False, c=True, d=None, e=None)


class TestIntFloatStrParam(ParamBase):
    """
    Test int, float and str cli_options.
    """

    @settings(kw_only=True)
    class Settings:
        a: str = option(default="spam")
        b: str = secret(default="spam")
        c: int = 0
        d: float = 0
        # Test explicit and implicit "Optional" variants
        e: Optional[str]
        f: Union[None, int] = None
        g: Union[int, None] = 0

    click_expected_help = [
        "  --a TEXT     [default: spam]",
        "  --b TEXT     [default: *******]",
        "  --c INTEGER  [default: 0]",
        "  --d FLOAT    [default: 0.0]",
        "  --e TEXT",
        "  --f INTEGER",
        "  --g INTEGER  [default: 0]",
    ]
    argparse_expected_help = [
        "  --a TEXT    [default: spam]",
        "  --b TEXT    [default: *******]",
        "  --c INT     [default: 0]",
        "  --d FLOAT   [default: 0.0]",
        "  --e TEXT",
        "  --f INT",
        "  --g INT     [default: 0]",
    ]

    env_vars = {"A": "eggs", "B": "bacon", "C": "42", "D": "3.14"}
    click_expected_env_var_defaults = [
        "  --a TEXT     [default: eggs]",
        "  --b TEXT     [default: *******]",
        "  --c INTEGER  [default: 42]",
        "  --d FLOAT    [default: 3.14]",
        "  --e TEXT",
        "  --f INTEGER",
        "  --g INTEGER  [default: 0]",
    ]
    argparse_expected_env_var_defaults = [
        "  --a TEXT    [default: eggs]",
        "  --b TEXT    [default: *******]",
        "  --c INT     [default: 42]",
        "  --d FLOAT   [default: 3.14]",
        "  --e TEXT",
        "  --f INT",
        "  --g INT     [default: 0]",
    ]

    expected_defaults = Settings(e=None)

    cli_options = ["--a=eggs", "--b=pwd", "--c=3", "--d=3.1"]
    expected_settings = Settings(a="eggs", b="pwd", c=3, d=3.1, e=None)


class TestDateTimeParam(ParamBase):
    """
    Test datetime cli_options.
    """

    @settings
    class Settings:
        a: datetime = datetime.fromtimestamp(0, timezone.utc)
        b: datetime = datetime.fromtimestamp(0, timezone.utc)
        c: datetime = datetime.fromtimestamp(0, timezone.utc)
        d: Optional[datetime] = None

    click_expected_help = [
        "  --a [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 1970-01-01T00:00:00+00:00]",  # noqa: E501
        "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 1970-01-01T00:00:00+00:00]",  # noqa: E501
        "  --c [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 1970-01-01T00:00:00+00:00]",  # noqa: E501
        "  --d [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
    ]
    argparse_expected_help = [
        "  --a YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: 1970-01-01T00:00:00+00:00]",
        "  --b YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: 1970-01-01T00:00:00+00:00]",
        "  --c YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: 1970-01-01T00:00:00+00:00]",
        "  --d YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
    ]

    env_vars = {
        "A": "2021-05-04T13:37:00Z",
        "B": "2021-05-04T13:37:00",
        "C": "2021-05-04",
    }
    click_expected_env_var_defaults = [
        "  --a [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 2021-05-04T13:37:00+00:00]",  # noqa: E501
        "  --b [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 2021-05-04T13:37:00]",  # noqa: E501
        "  --c [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 2021-05-04T00:00:00]",  # noqa: E501
        "  --d [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
    ]
    argparse_expected_env_var_defaults = [
        "  --a YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: 2021-05-04T13:37:00+00:00]",
        "  --b YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: 2021-05-04T13:37:00]",
        "  --c YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: 2021-05-04T00:00:00]",
        "  --d YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
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


class TestEnumParam(ParamBase):
    """
    Test enum cli_options
    """

    @settings
    class Settings:
        a: LeEnum
        b: Optional[LeEnum]
        c: LeEnum = LeEnum.spam

    click_expected_help = [
        "  --a [spam|eggs]  [required]",
        "  --b [spam|eggs]",
        "  --c [spam|eggs]  [default: spam]",
    ]
    argparse_expected_help = [
        "  --a {spam,eggs}  [required]",
        "  --b {spam,eggs}",
        "  --c {spam,eggs}  [default: spam]",
    ]

    env_vars = {"A": "spam", "C": "eggs"}
    click_expected_env_var_defaults = [
        "  --a [spam|eggs]  [default: spam]",
        "  --b [spam|eggs]",
        "  --c [spam|eggs]  [default: eggs]",
    ]
    argparse_expected_env_var_defaults = [
        "  --a {spam,eggs}  [default: spam]",
        "  --b {spam,eggs}",
        "  --c {spam,eggs}  [default: eggs]",
    ]

    default_options = ["--a=spam"]
    expected_defaults = Settings(a=LeEnum.spam, b=None)

    cli_options = ["--a=spam", "--c=eggs"]
    expected_settings = Settings(LeEnum.spam, None, LeEnum.eggs)


class TestPathParam(ParamBase):
    """
    Test Path cli_options
    """

    @settings
    class Settings:
        a: Path
        b: Path = Path("/")
        c: Optional[Path] = None

    click_expected_help = [
        "  --a PATH  [required]",
        "  --b PATH  [default: /]",
        "  --c PATH",
    ]
    argparse_expected_help = [
        "  --a PATH    [required]",
        "  --b PATH    [default: /]",
        "  --c PATH",
    ]

    env_vars = {"A": "/spam/eggs"}
    click_expected_env_var_defaults = [
        "  --a PATH  [default: /spam/eggs]",
        "  --b PATH  [default: /]",
        "  --c PATH",
    ]
    argparse_expected_env_var_defaults = [
        "  --a PATH    [default: /spam/eggs]",
        "  --b PATH    [default: /]",
        "  --c PATH",
    ]

    default_options = ["--a=/"]
    expected_defaults = Settings(Path("/"))

    cli_options = ["--a=/spam"]
    expected_settings = Settings(Path("/spam"))


class TestNestedParam(ParamBase):
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

    click_expected_help = [
        "  --n-a TEXT     [default: nested]",
        "  --n-b INTEGER  [default: 0]",
    ]
    argparse_expected_help = [
        "  --n-a TEXT  [default: nested]",
        "  --n-b INT   [default: 0]",
    ]

    env_vars = {"N_A": "spam", "N_B": "42"}
    click_expected_env_var_defaults = [
        "  --n-a TEXT     [default: spam]",
        "  --n-b INTEGER  [default: 42]",
    ]
    argparse_expected_env_var_defaults = [
        "  --n-a TEXT  [default: spam]",
        "  --n-b INT   [default: 42]",
    ]

    expected_defaults = Settings()

    cli_options = ["--n-a=eggs", "--n-b=3"]
    expected_settings = Settings(Settings.Nested("eggs", 3))


class TestListParam(ParamBase):
    """
    Lists (and friends) use "multiple=True".
    """

    @settings
    class Settings:
        a: List[int]
        b: Optional[List[int]]
        c: Optional[List[int]] = None
        d: Optional[List[int]] = []
        e: Sequence[datetime] = [datetime(2020, 5, 4)]
        f: MutableSequence[int] = []
        g: Set[int] = set()
        h: MutableSet[int] = set()
        i: FrozenSet[int] = frozenset()

    click_expected_help = [
        "  --a INTEGER",
        "  --b INTEGER",
        "  --c INTEGER",
        "  --d INTEGER",
        "  --e [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 2020-05-04T00:00:00]",
        "  --f INTEGER",
        "  --g INTEGER",
        "  --h INTEGER",
        "  --i INTEGER",
    ]
    argparse_expected_help = [
        "  --a INT               [default: []]",
        "  --b INT               [default: []]",
        "  --c INT               [default: []]",
        "  --d INT               [default: []]",
        "  --e YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: ['2020-05-04T00:00:00']]",
        "  --f INT               [default: []]",
        "  --g INT               [default: []]",
        "  --h INT               [default: []]",
        "  --i INT               [default: []]",
    ]

    env_vars = {
        "A": "1:2",
        "E": "2021-01-01:2021-01-02",  # Dates with times wont work here!
    }
    click_expected_env_var_defaults = [
        "  --a INTEGER                     [default: 1, 2]",
        "  --b INTEGER",
        "  --c INTEGER",
        "  --d INTEGER",
        "  --e [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%dT%H:%M:%S%z]",
        "                                  [default: 2021-01-01T00:00:00,",
        "                                  2021-01-02T00:00:00]",
        "  --f INTEGER",
        "  --g INTEGER",
        "  --h INTEGER",
        "  --i INTEGER",
    ]
    argparse_expected_env_var_defaults = [
        "  --a INT               [default: [1, 2]]",
        "  --b INT               [default: []]",
        "  --c INT               [default: []]",
        "  --d INT               [default: []]",
        "  --e YYYY-MM-DD[Thh:mm:ss[+xx:yy]]",
        "                        [default: ['2021-01-01T00:00:00',",
        "                        '2021-01-02T00:00:00']]",
        "  --f INT               [default: []]",
        "  --g INT               [default: []]",
        "  --h INT               [default: []]",
        "  --i INT               [default: []]",
    ]

    default_options = ["--a=1"]
    # click always gives us an empty list, never "None"
    expected_defaults = Settings(a=[1], b=[], c=[])

    cli_options = [
        "--a=1",
        "--a=2",
        "--e=2020-01-01",
        "--e=2020-01-02",
        "--f=3",
        "--g=4",
        "--h=5",
        "--i=6",
    ]
    expected_settings = Settings(
        [1, 2],
        [],  # click always gives us an empty list, never "None"
        [],  # click always gives us an empty list, never "None"
        [],
        [datetime(2020, 1, 1), datetime(2020, 1, 2)],
        [3],
        {4},
        {5},
        frozenset({6}),
    )


class TestTupleParam(ParamBase):
    """
    Tuples are handled either like the list variant with multiple=True or
    like the struct variant with nargs=x.
    """

    @settings
    class Settings:
        a: Tuple[int, ...] = (0,)
        b: Tuple[int, float, str] = (0, 0.0, "")
        c: Optional[Tuple[int, float, str]] = None

    click_expected_help = [
        "  --a INTEGER                  [default: 0]",
        "  --b <INTEGER FLOAT TEXT>...  [default: 0, 0.0, ]",
        "  --c <INTEGER FLOAT TEXT>...",
    ]
    argparse_expected_help = [
        "  --a INT             [default: [0]]",
        "  --b INT FLOAT TEXT  [default: (0, 0.0, '')]",
        "  --c INT FLOAT TEXT",
    ]

    env_vars = {"A": "1:2", "B": "42:3.14:spam"}
    click_expected_env_var_defaults = [
        "  --a INTEGER                  [default: 1, 2]",
        "  --b <INTEGER FLOAT TEXT>...  [default: 42, 3.14, spam]",
        "  --c <INTEGER FLOAT TEXT>...",
    ]
    argparse_expected_env_var_defaults = [
        "  --a INT             [default: [1, 2]]",
        "  --b INT FLOAT TEXT  [default: (42, 3.14, 'spam')]",
        "  --c INT FLOAT TEXT",
    ]

    expected_defaults = Settings()

    cli_options = ["--a=1", "--a=2", "--b", "1", "2.3", "spam"]
    expected_settings = Settings((1, 2), (1, 2.3, "spam"))

    def test_wrong_default_length(self):
        """
        Default values for tuples must have the exact shape defined in by
        their type.

        Too long tuples are automatically truncated (by attrs or click),
        but too short default values are an error.
        """

        @settings
        class Settings:
            a: Tuple[int, int, int] = (0, 1)  # type: ignore

        run = make_cli(Settings)

        p = "Invalid default for type typing.Tuple[int, int, int]: (0, 1)"
        with pytest.raises(ValueError, match=re.escape(p)):
            run("--help")


class TestNestedTupleParam(ParamBase):
    """
    Lists of tuples use "multiple=True" and "nargs=x".
    """

    @settings
    class Settings:
        a: List[Tuple[int, int]] = option(factory=list)

    click_expected_help = [
        "  --a <INTEGER INTEGER>...",
    ]
    argparse_expected_help = [
        "  --a INT INT  [default: []]",
    ]

    # A list of tuples cannot be loaded with the default converter,
    # so we skip this test here.
    env_vars: Dict[str, Any] = {}
    click_expected_env_var_defaults = [
        "  --a <INTEGER INTEGER>...",
    ]
    argparse_expected_env_var_defaults = [
        "  --a INT INT  [default: []]",
    ]

    expected_defaults = Settings()

    cli_options = ["--a", "1", "2", "--a", "3", "4"]
    expected_settings = Settings([(1, 2), (3, 4)])


class TestDictParam(ParamBase):
    """
    Dict params use "="-spearated key-value pairs and "multiple=True".
    """

    @settings
    class Settings:
        a: Dict[str, str]  # Test "None" value
        b: Dict[str, str] = {}  # Test empty value
        c: Dict[str, str] = {"default": "value"}
        d: Optional[Dict[str, str]] = None

    click_expected_help = [
        "  --a KEY=VALUE",
        "  --b KEY=VALUE",
        "  --c KEY=VALUE  [default: default=value]",
        "  --d KEY=VALUE",
    ]
    argparse_expected_help = [
        "  --a KEY=VALUE  [default: ]",
        "  --b KEY=VALUE  [default: ]",
        "  --c KEY=VALUE  [default: default=value]",
        "  --d KEY=VALUE  [default: ]",
    ]

    # A dictionary cannot be loaded with the default converter,
    # so we skip this test here.
    env_vars: Dict[str, Any] = {}
    click_expected_env_var_defaults = [
        "  --a KEY=VALUE",
        "  --b KEY=VALUE",
        "  --c KEY=VALUE  [default: default=value]",
        "  --d KEY=VALUE",
    ]
    argparse_expected_env_var_defaults = [
        "  --a KEY=VALUE  [default: ]",
        "  --b KEY=VALUE  [default: ]",
        "  --c KEY=VALUE  [default: default=value]",
        "  --d KEY=VALUE  [default: ]",
    ]

    default_options = ["--a=k=v"]
    expected_defaults = Settings({"k": "v"}, d={})  # "d" is never None

    cli_options = [
        "--a",
        "key0=val0",
        "--c",
        "key1=val1",
        "--c",
        "key-2=val-2",
        "--c",
        "key 3=oi oi",
    ]
    expected_settings = Settings(
        {"key0": "val0"},
        {},
        {"key1": "val1", "key-2": "val-2", "key 3": "oi oi"},
        {},
    )


class TestNoTypeParam(ParamBase):
    """
    Test option without type annotation.
    """

    @settings
    class Settings:
        a = option(default="spam")  # type: ignore

    click_expected_help = [
        "  --a TEXT  [default: spam]",
    ]
    argparse_expected_help = [
        "  --a A       [default: spam]",
    ]

    env_vars = {"A": "eggs"}
    click_expected_env_var_defaults = [
        "  --a TEXT  [default: eggs]",
    ]
    argparse_expected_env_var_defaults = [
        "  --a A       [default: eggs]",
    ]

    expected_defaults = Settings("spam")  # type: ignore

    cli_options = ["--a=eggs"]
    expected_settings = Settings(a="eggs")  # type: ignore


@pytest.fixture(params=ParamBase.classes)
def param_cls(request: pytest.FixtureRequest) -> Type[ParamBase]:
    return request.param


class TestClick:

    prefix = "click"

    @pytest.fixture
    def cli(self, param_cls: Type[ParamBase]) -> Cli:
        return make_cli(param_cls.Settings)

    def test_help(self, param_cls: Type[ParamBase], cli: Cli[ST]):
        """
        The genereated CLI has a proper help output.
        """
        result = cli("--help")

        assert result.output.splitlines()[:-1] == [
            "Usage: cli [OPTIONS] COMMAND [ARGS]...",
            "",
            "Options:",
        ] + param_cls.get_expected_help(self.prefix)

    def test_defaults_from_envvars(
        self,
        param_cls: Type[ParamBase],
        cli: Cli[ST],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """
        Previously loaded settings (e.g., from env vars) can be converted
        to click options.

        Regression test for #11
        """
        for var, val in param_cls.env_vars.items():
            monkeypatch.setenv(f"TEST_{var}", val)

        result = cli("--help")

        assert result.output.splitlines()[:-1] == [
            "Usage: cli [OPTIONS] COMMAND [ARGS]...",
            "",
            "Options:",
        ] + param_cls.get_expected_env_var_defaults(self.prefix)

    def test_defaults(self, param_cls: Type[ParamBase], cli: Cli[ST]):
        """
        Arguments of the generated CLI have default values.
        """
        result = cli(*param_cls.default_options)
        assert result.output == ""
        assert result.settings == param_cls.expected_defaults

    def test_options(self, param_cls: Type[ParamBase], cli: Cli[ST]):
        """
        Default values can be overriden by passing the corresponding args.
        """
        result = cli(*param_cls.cli_options)
        assert result.output == ""
        assert result.settings == param_cls.expected_settings


class TestArgparse:

    prefix = "argparse"

    @pytest.fixture
    def arg_parser(self, param_cls: Type[ParamBase]) -> ArgParser:
        return make_argparser(param_cls.Settings)

    def test_help(
        self,
        param_cls: Type[ParamBase],
        arg_parser: ArgParser,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """
        The genereated CLI has a proper help output.
        """
        with pytest.raises(SystemExit):
            arg_parser("--help")
        out, err = capsys.readouterr()
        print(out)
        assert err == ""

        lines: List[str] = []
        for line in out.splitlines():
            if line.startswith("  --") or lines:
                lines.append(line)
        assert lines == param_cls.get_expected_help(self.prefix)

    def test_defaults_from_envvars(
        self,
        param_cls: Type[ParamBase],
        arg_parser: ArgParser,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """
        Previously loaded settings (e.g., from env vars) can be converted
        to click options.

        Regression test for #11
        """
        for var, val in param_cls.env_vars.items():
            monkeypatch.setenv(f"TEST_{var}", val)

        with pytest.raises(SystemExit):
            arg_parser("--help")
        out, err = capsys.readouterr()
        print(out)

        lines: List[str] = []
        for line in out.splitlines():
            if line.startswith("  --") or lines:
                lines.append(line)
        assert lines == param_cls.get_expected_env_var_defaults(self.prefix)

    def test_defaults(
        self,
        param_cls: Type[ParamBase],
        arg_parser: ArgParser,
    ):
        """
        Arguments of the generated CLI have default values.
        """
        result = arg_parser(*param_cls.default_options)
        assert result == param_cls.expected_defaults

    def test_options(
        self,
        param_cls: Type[ParamBase],
        arg_parser: ArgParser,
    ):
        """
        Default values can be overriden by passing the corresponding args.
        """
        result = arg_parser(*param_cls.cli_options)
        assert result == param_cls.expected_settings
