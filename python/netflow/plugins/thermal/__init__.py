"""netflow.thermal — thermal-resistance-network plugin.

State variable per node: temperature in Kelvin.
Sign convention: edges measure heat flux in Watts, positive a→b.

Public surface:

    from netflow.thermal import (
        # edges
        PlanarConduction, CylindricalConduction,
        ContactResistance, Fouling, UAEdge, Radiation, ForcedConvection,
        # fluids
        Fluid, CoolPropFluid, CallableFluid,
        # materials
        Material, Constant, SS316L, Zircaloy4, UO2, Helium_gap, Air,
        # components
        MultilayerCylindricalWall, InsulatedPipeSection, FuelRod,
        ResistanceStack,
        # helpers
        lmtd, effectiveness_ntu,
    )

The plugin imports only from ``netflow.core`` and (optionally) ``CoolProp``.
``CoolProp`` is imported lazily inside ``CoolPropFluid`` only; the module
remains importable without it.
"""

from netflow.plugins.thermal.edges import (
    ContactResistance,
    CoolantAdvection,
    CoolantMixing,
    CylindricalConduction,
    Fouling,
    PlanarConduction,
    Radiation,
    UAEdge,
    ForcedConvection,
)
from netflow.plugins.thermal.fluids import CallableFluid, CoolPropFluid, Fluid
from netflow.plugins.thermal.materials import (
    Air,
    Constant,
    Helium_gap,
    Material,
    SS316L,
    UO2,
    Zircaloy4,
)
from netflow.plugins.thermal.components import (
    FuelRod,
    InsulatedPipeSection,
    MultilayerCylindricalWall,
    ResistanceStack,
)
from netflow.plugins.thermal.helpers import effectiveness_ntu, lmtd

__all__ = [
    "PlanarConduction",
    "CylindricalConduction",
    "ContactResistance",
    "Fouling",
    "UAEdge",
    "Radiation",
    "ForcedConvection",
    "CoolantAdvection",
    "CoolantMixing",
    "Fluid",
    "CoolPropFluid",
    "CallableFluid",
    "Material",
    "Constant",
    "SS316L",
    "Zircaloy4",
    "UO2",
    "Helium_gap",
    "Air",
    "MultilayerCylindricalWall",
    "InsulatedPipeSection",
    "FuelRod",
    "ResistanceStack",
    "lmtd",
    "effectiveness_ntu",
]
