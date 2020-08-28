from attr import frozen, field

import typed_settings as ts


def test_load_settings(tmp_path):
    """Test basic functionality"""
    @frozen
    class Host:
        name: str
        port: int = field(converter=int)


    @frozen(kw_only=True)
    class Settings:
        url: str
        default: int = 3
        host: Host = field(converter=lambda d: Host(**d) if isinstance(d, dict) else d)

    config_file = tmp_path.joinpath('settings.toml')
    config_file.write_text("""[example]
        url = "https://example.com"
        [example.host]
        name = "example.com"
        port = 443
    """)

    settings = ts.load_settings(
        settings_cls=Settings, appname='example', config_files=[config_file]
    )
    assert settings == Settings(
        url='https://example.com',
        default=3,
        host=Host(
            name='example.com',
            port=443,
        ),
    )
