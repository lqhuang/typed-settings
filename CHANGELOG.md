# Changelog

## 0.6 (2020-10-11)

- ✨ Add `pass_settings` decorator that pass settings to nested Click commands.
- 📝 Initialize documentaion at https://typed-settings.readthedocs.io
- 📝 Improve README and automatically test examples

## 0.5 (2020-09-30)

- ✨ Click options for basic data types (`bool`, `int`, `str`, `Enum`) can be generated now.
- 🐛 Fix bug that prevented nested settings classes from automatically being instantiated when no settings for them were loaded.

## 0.4 (2020-09-25)

- ✨ Add convenience wrappers for attrs:
  - `settings` is an alias for `attr.frozen`
  - `option` is an alias for `attr.field`
  - `secret` is an alias for `attr.field` and masks the options's value with `***` when the settings classes is printed.
- ✨ Add `update_settings()` method which is useful for overriding settings in tests.
- ✨ Mandatory config files can be prefixed with `!` (e.g., `!./credentials.toml`).
  An error is raised if a mandatory config file does not exist.
- 💥 Flip *appname* and *settings_cls* args of `load_settings()`.
- ♻️ Refactor internals to improve extensibility.
- 🚀 Add pre-commit hooks


## 0.3 (2020-09-17)

- 📦 Improve packaging
- 👷 Add code linting and improve CI
- ♻️ Refactorings


## 0.2 (2020-09-02)

- ✨ Make sure env vars can be read
- ✅ Add tests for `load_settings()`


## 0.1 (2020-08-28)

- 🎉 Initial PoC
