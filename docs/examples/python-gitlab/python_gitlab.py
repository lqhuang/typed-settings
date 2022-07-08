# python_gitlab.py

import typed_settings as ts


@ts.settings
class GlobalSettings:
    default: str
    ssl_verify: bool = True


@ts.settings
class GitlabAccountSettings:
    url: str
    private_token: str = ts.secret()
    api_version: int = 3


appname = "python-gitlab"
# config_files = [platformdirs.user_config_path().joinpath(f"{appname}.toml")]
config_files = [f"{appname}.toml"]

global_settings = ts.load(
    GlobalSettings,
    appname=appname,
    config_files=config_files,
    config_file_section="global",
)
account_settings = ts.load(
    GitlabAccountSettings,
    appname=appname,
    config_files=config_files,
    config_file_section=global_settings.default,
)
print(global_settings)
print(account_settings)
