# python_gitlab.py

import typed_settings as ts


@ts.settings
class GitlabSettings:
    url: str
    private_token: str = ts.secret()
    api_version: int = 3


@ts.settings
class GlobalSettings:
    default: str
    ssl_verify: bool = True


global_settings = ts.load(
    GlobalSettings,
    appname="gitlab",
    config_files=["python-gitlab.toml"],
    config_file_section="global",
)
gitlab_settings = ts.load(
    GitlabSettings,
    appname="gitlab",
    config_files=["python-gitlab.toml"],
    config_file_section=global_settings.default,
)
print(global_settings)
print(gitlab_settings)
