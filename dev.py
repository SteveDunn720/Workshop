import logging
import sys

from Workshop..build.mgear_api.reload import reload_components

log = logging.getLogger(__name__)


def reload_Workshop.() -> None:
    """
    This removes all the Workshop. modules so that on next import they will be updated.
    Useful when making live changes and wanting to test without re-starting Maya.
    """
    module_names = [name for name in sys.modules if name.startswith("Workshop.")]
    for name in module_names:
        if name in sys.modules:
            log.info(f"Unloading {name}")
            del sys.modules[name]
    log.info("Reloaded Workshop. python modules")


def reload() -> None:
    """
    This removes all the Workshop. modules, as well as reloading the mGear components.
    Useful when making live changes and wanting to test without re-starting Maya.

    IMPORTANT: This does NOT re-import Workshop. as a library.
    """
    reload_Workshop.()
    reload_components()
