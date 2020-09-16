from functools import update_wrapper


def click_options(settings_cls, appname, config_files):
    try:
        import click
    except ImportError as e:
        raise ModuleNotFoundError(
            'You need to install "click" to use this feature'
        ) from e

    def pass_settings(f):
        """Similar to :func:`pass_context`, but only pass the object on the
        context onwards (:attr:`Context.obj`).  This is useful if that object
        represents the state of a nested system.
        """

        def new_func(*args, **kwargs):
            return f(
                click.get_current_context().obj["settings"], *args, **kwargs
            )

        return update_wrapper(new_func, f)

    def cb(c, p, v):
        if c.obj is None:
            c.obj = {}
        if "settings" not in c.obj:
            c.obj[
                "settings"
            ] = {}  # typed_settings.load_settings(cls=settings_cls)
        c.obj["settings"][p.name] = v
        return v

    def wrap(f):
        f = click.option(
            "--spam", callback=cb, expose_value=False, is_eager=True
        )(f)
        f = click.option(
            "--eggs", callback=cb, expose_value=False, is_eager=True
        )(f)
        f = pass_settings(f)
        return f

    return wrap
