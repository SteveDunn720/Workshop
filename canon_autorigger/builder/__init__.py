"""Workshop rig builder package."""


def show_ui(*args, **kwargs):
    """Open the builder in Maya, importing Qt only when needed."""
    from .ui import show_ui as open_ui

    return open_ui(*args, **kwargs)
