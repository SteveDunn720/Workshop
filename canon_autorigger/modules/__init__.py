
from . import root as root
from . import biped_limb as biped_limb
from . import hip as hip
from . import foot as foot
from . import spine as spine
from . import clav as clav
from . import hand as hand
from . import chain as chain
from . import metacarpal as metacarpal
from . import neck as neck
from . import head as head
from . import ik_correctives
from . import face
from . import jaw
from . import mouth
from . import nose
from . import arch
from . import tongue
from . import nl_fold
from . import brow
from . import cheek
from . import ear
from . import arbit as arbit
from . import hip_cor as hip_cor
from . import knee_cor as knee_cor

from .root import Root
from .biped_limb import Biped_Limb
from .hip import Hip
from .foot import Foot
from .spine import Spine
from .clav import Clav
from .hand import Hand
from .chain import Chain
from .metacarpal import Metacarpal
from .neck import Neck
from .head import Head
from .ik_correctives import Ik_correctives
from .face import Face
from .jaw import Jaw
from .mouth import Mouth
from .nose import Nose
from .arch import Arch
from .tongue import Tongue
from .nl_fold import NL_Fold
from .brow import Brow
from .cheek import Cheek
from .ear import Ear
from .arbit import Arbit
from .hip_cor import Hip_Cor
from .knee_cor import Knee_Cor




__all__ = [
"root", #rig_root
"Root", #rig_root class
"biped_limb",
"Biped_Limb",
"hip",
"Hip",
"foot",
"Foot",
"spine",
"Spine",
"clav",
"Clav",
"hand",
"Hand",
"chain",
"Chain",
"metacarpale",
"Metacarpal",
"neck",
"Neck",
"head",
"Head",
"ik_correctives",
"Ik_correctives",
"face",
"Face",
"jaw",
"Jaw",
"mouth",
"Mouth",
"nose",
"Nose",
"arch",
"Arch",
"tongue",
"Tongue",
"nl_fold",
"NL_Fold",
"brow",
"Brow",
"cheek",
"Cheek",
"ear",
"Ear",
"arbit",
"Arbit",
"hip_cor",
"Hip_Cor",
"knee_cor",
"Knee_Cor",
]

MODULE_CLASSES = [
    Root,
    Biped_Limb,
    Hip,
    Foot,
    Spine,
    Clav,
    Hand,
    Chain,
    Metacarpal,
    Neck,
    Head,
    Ik_correctives,
    Face,
    Jaw,
    Mouth,
    Nose,
    Arch,
    Tongue,
    NL_Fold,
    Brow,
    Cheek,
    Ear,
    Arbit,
]


MODULE_REGISTRY = {
    cls.MODULE_NAME: cls
    for cls in MODULE_CLASSES
    if hasattr(cls, "MODULE_NAME")
}


def get_module_class(module: str):
    try:
        return MODULE_REGISTRY[module]
    except KeyError:
        raise ValueError(
            f"Unknown rig module: {module}"
        )