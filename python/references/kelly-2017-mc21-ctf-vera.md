---
id: kelly-2017-mc21-ctf-vera
csl: references.json#kelly-2017-mc21-ctf-vera
access: public                        # open access (CC BY-NC-ND)
retrieved: 2026-05-20
file: kelly-2017-mc21-ctf-vera.pdf    # extracted text: kelly-2017-mc21-ctf-vera.txt
grounds:
  - netflow fuel-temperature comparison
  - netflow coolant-spread comparison
  - netflow power-peaking and eigenvalue context
key-values:
  - value: 1065.8 C
    defines: P7 maximum VOLUME-AVERAGE fuel pin temperature (NOT centerline)
    status: verified
    locus: Fig. 24, sec. 4.2.2
  - value: ~6.6 K (MC21/CTF & VERA); ~8.7 K (MC21/COBRA-IE)
    defines: P6 subchannel exit coolant temperature spread (max-min)
    status: figure-derived
    locus: Fig. 11
  - value: 1.92 (3-D local); 1.37 (radial)
    defines: P7 pin-power peaking
    status: verified
    locus: Figs. 17, 16
  - value: 1.16424 (MC21); 1.16361 (MPACT/VERA, -63 pcm)
    defines: P6 eigenvalue (quarter-assembly, HFP) — code solutions, not reference
    status: verified
    locus: Table 1
  - value: ~34-37 K
    defines: P6 assembly coolant temperature rise to exit
    status: figure-derived
    locus: Fig. 11 / spec core-avg
related: [[godfrey-2014-vera-spec]], [[aviles-2017-mc21-cobra-ie]]
---
The open-access code-solution paper netflow compares against. Source of the
volume-average fuel temperature (the correct quantity — the note's "centerline
2474 K" was unsourced and wrong) and the figure-derived coolant spread (the real
anchor for the withdrawn "8.3 K"). Reports code-to-code agreement, not a reference
truth — consistent with [[godfrey-2014-vera-spec]]'s "no reference solution." Does
not publish an absolute P6 fuel temperature or a centerline profile.
