from Workshop.canon_autorigger.modules import get_module_class
from Workshop.guide.resolver import ModuleInstance


def preview_module_instance(
    instance: ModuleInstance,
) -> dict[str, list[str]]:

    module_class = get_module_class(
        instance.module
    )

    return module_class.preview(
        part=instance.part,
        side=instance.side,
    )