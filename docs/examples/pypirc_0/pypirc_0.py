# pypirc_0.py

import sys
from typing import List

import typed_settings as ts


@ts.settings
class RepoServer:
    repository: str
    username: str
    password: str = ts.secret(default="")


@ts.settings
class Settings:
    index_servers: List[str]


settings = ts.load(Settings, "distutils", ["pypirc.toml"])
repos = {
    name: ts.load(RepoServer, name, ["pypirc.toml"])
    for name in settings.index_servers
}
REPO_NAME = sys.argv[1]
print(repos[REPO_NAME])
