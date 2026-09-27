from Workshop.canon_autorigger.modules import get_module_class
from Workshop.guide.resolver import ModuleInstance
from .module_schema import get_setting_value



def get_preview_settings(
    instance: ModuleInstance,
    module_class,
) -> dict:
    return {
        setting.name: get_setting_value(
            instance,
            module_class,
            setting.name,
        )
        for setting in module_class.SETTINGS
    }


def preview_module_instance(
    instance: ModuleInstance,
) -> dict:

    module_class = get_module_class(
        instance.module
    )

    settings = get_preview_settings(
        instance,
        module_class,
    )

    return module_class.preview(
        part=instance.part,
        side=instance.side,
        guides=instance.guides,
        settings=settings,
    )