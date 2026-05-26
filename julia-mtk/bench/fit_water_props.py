"""Fit water mu(T), k_f(T), Pr(T) at 15.5 MPa over the subcooled-liquid band that
brackets the convection film temperature (~602 K), so the MTK port reproduces
netflow's Dittus-Boelter h without CoolProp.jl. Prints Julia-ready coefficients
and verifies the fit reproduces netflow's h. Reads frozen netflow.
"""
import sys, math
import numpy as np
sys.path.insert(0, "/home/fig/soultest")
from netflow.plugins.thermal import CoolPropFluid

P = 15.5e6
fluid = CoolPropFluid("Water", default_P=P)
Ts = np.array([585.0, 590.0, 595.0, 600.0, 605.0, 610.0])  # subcooled liquid, brackets 602
mu = np.array([fluid.mu(T, P) for T in Ts])
kf = np.array([fluid.k(T, P)  for T in Ts])
Pr = np.array([fluid.Pr(T, P) for T in Ts])

# quadratic fits in T
cmu = np.polyfit(Ts, mu, 2)
ckf = np.polyfit(Ts, kf, 2)
cPr = np.polyfit(Ts, Pr, 2)

def jl(name, c):
    # c = [a2, a1, a0] for a2*T^2 + a1*T + a0
    print(f"{name}(T) = {c[0]:.10e}*T^2 + {c[1]:.10e}*T + {c[2]:.10e}")

print("# Julia-ready quadratic fits, water @ 15.5 MPa, valid ~585-610 K:")
jl("mu", cmu); jl("kf", ckf); jl("Pr_", cPr)

# verify: reproduce netflow's Dittus-Boelter h at the film temperature
mdot, D_h, A_ht = 0.30, 12.0e-3, 3.14e-2
A_xs = math.pi * D_h**2 / 4
def h_of(Tf):
    mu_ = np.polyval(cmu, Tf); kf_ = np.polyval(ckf, Tf); Pr_ = np.polyval(cPr, Tf)
    Re = mdot * D_h / (mu_ * A_xs)
    Nu = 0.023 * Re**0.8 * Pr_**0.4   # heating
    return Nu * kf_ / D_h
Tf = 602.351
print(f"\nfit h(T_film={Tf}) = {h_of(Tf):.3f} W/m^2-K   (netflow: 30650.571)")
print(f"max fit error: mu {np.max(np.abs(np.polyval(cmu,Ts)-mu)/mu)*100:.3f}%  "
      f"kf {np.max(np.abs(np.polyval(ckf,Ts)-kf)/kf)*100:.3f}%  "
      f"Pr {np.max(np.abs(np.polyval(cPr,Ts)-Pr)/Pr)*100:.3f}%")
