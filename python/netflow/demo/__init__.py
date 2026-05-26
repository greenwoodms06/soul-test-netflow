"""netflow.demo — minimal demo plugin used by tests.

A scalar-diffusion / resistor-mesh primitive that exercises the
Edge / Network / solver protocol without any domain-specific
dependencies. The thermal plugin (``netflow.thermal``) is the real
demonstration of the abstraction; this one exists so the core has a
trivial plugin to test against.
"""

from netflow.demo.resistor import LinearResistor, build_resistor_mesh

__all__ = ["LinearResistor", "build_resistor_mesh"]
