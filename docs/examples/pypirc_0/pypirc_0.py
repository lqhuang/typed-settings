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


REPO_NAME = sys.argv[1]
repo_server = ts.load(RepoServer, REPO_NAME, ["pypirc.toml"])
print(repo_server)
