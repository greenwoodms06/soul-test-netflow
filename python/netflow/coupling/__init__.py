"""netflow.coupling — multi-plugin coupled solves.

Code here orchestrates *multiple* domain plugins (e.g. Picard-coupled
hydraulic <-> thermal). It sits ABOVE the plugin layer: unlike a plugin,
it is allowed to import more than one plugin, because its whole purpose
is to couple them. Plugins themselves remain peers that never import
each other.
"""
