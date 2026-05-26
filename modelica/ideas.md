# ideas.md — forward-looking inbox

Jot with `/soul-idea`. Graduate to a Finding when earned.

## Open

- **Generated-C compile time as a Dymola wall (cc1 -O0 / tcc mitigation).**
  Step 2 of the 2026-05-26 unfreeze closed the Dymola-flag side (MO-F16: no
  `Advanced.*` flag moves the cc1-bound wall). The toolchain side remains:
  `gcc -O0` (likely halves cc1 cost at a slower dymosim) or `tcc` (very
  fast compile, runtime cost) is the open question. Probe via direct
  `gccCompilerOptions` injection or by editing `dsbuild.sh`.
- ~~**Algebraic-loop init solver as the wall on long axial chains.**~~
  CLOSED 2026-05-26 (MO-F15): `Advanced.Translation.SparseActivate = true`
  rescued the N=5000 chain that previously hard-failed at defaults; cut
  N=2500 wall by 2.2× (197 s → 90 s).
- ~~**Advanced-flag dogfood (separate experiment).**~~ CLOSED 2026-05-26
  (MO-F15 + MO-F16). Sparse-solver effect characterized at all three walls;
  Cvode/Esdirk23a integrators paired with sparse perform similarly;
  ParallelizeCode marginal at compile-bound scales; looser tolerance
  unaffected. KLU vs Pardiso (`Hidden.SparseSolverType`) NOT differentiated
  — open if a particular subchannel scenario needs the comparison.
- ~~**17×17×30 with axial conduction across pins.**~~ CLOSED 2026-05-26
  (MO-F17): `AssemblyVeraP6CrossPin` at 17×17×30 = 543 s (+25 % vs vanilla).
- **OpenModelica leg.** Same `.mo` package, different translator/codegen.
  Removes the Dymola vendor caveat; isolates "Modelica as a language" from
  "Dymola as an implementation." Light: should be hours, not days — the
  models are MSL-only.
- **Guide-tube bypass topology** (MO-F21 follow-on). The current
  `AssemblyVeraP6` models all 289 positions as fuel rods; Kelly P6's 6.6 K
  outlet spread is dominated by the 24 guide-tube + 1 instrument-tube
  bypass that redistributes flow across the assembly. Adding inert
  (no-power, possibly different K_loss) channels at the VERA guide-tube
  positions would close the structural gap to an apples-to-apples
  comparison with Kelly's spread.
- **Axial peaking + radial peaking combined for the hot-pin volavg vs Kelly
  P7's 1066 °C** (MO-F21 follow-on). Apply Kelly's 1.37 radial × 1.40 axial
  (3D peaking 1.92) and re-run AssemblyVeraP6 to test the peak-volavg
  comparison directly.
- **Calibrated lateral conductance in subchannel model** (MO-F19 follow-on).
  `LateralFlowLink.G` currently set to 1e-5 kg/(s·Pa) as a topology-test
  value. Physically meaningful G would need calibration against CTF or
  netflow's subchannel closure. A radial-power-peaked test case would also
  surface non-trivial lateral m_flow (uniform power → 0 by symmetry).
- **Pin-by-pin neutronics at full 17×17×30 transient** (MO-F18 follow-on).
  Step 3b ran at 17×17×10 in 135 s (50 s transient). Full 17×17×30 transient
  estimated > 2000 s; deferred to a focused experiment if the Body wants
  the timing characterization.
- **Scale past 25×25** (33×33×30 = 32 670 pin nodes). Extrapolating the
  measured 1.38 high-end exponent, 33×33×30 probably hits the 16 GB RAM
  ceiling cc1 has been pushing. Step 4 of the 2026-05-26 unfreeze covers
  25×25×30; 33×33 remains open and likely needs `gcc -O0` or `tcc`
  mitigation before being feasible.

## Soul-meta observations (not yet graduated)

- **Coherent Falsehood on measurement: the "wall-time only" trap.** Wrote a
  stress test that measured wall-clock time and called it complete. A model
  that ran successfully but returned garbage numbers would have passed.
  Caught by `/soul-verify` the next turn; fixed in ~2 min with
  `test/verify_assembly_physics.py`. Worth a Soul finding once a second
  instance lands — pattern is "I measured X about the run; the run might
  have been wrong." Specific shape: *measurement of meta-properties
  (time, size, log output) without measurement of physics.*
- **Benchmark-anchor framing as load-bearing context.** Dymola's 397 s reads
  as "fast" only against Julia's 25–40 min extrapolation. Absent that
  anchor 397 s is just a number. The COMPARISON.md document IS the
  load-bearing context — without it, a reader has no way to tell whether
  this result matters. Worth a Soul finding on *which artifact carries the
  framing for any cross-paradigm benchmark.*
