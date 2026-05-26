---
id: aviles-2017-mc21-cobra-ie
csl: references.json#aviles-2017-mc21-cobra-ie
access: provided-by-body              # paywalled (Elsevier); provided by the Body 2026-05-20
retrieved: 2026-05-20
file: aviles-2017-mc21-cobra-ie.pdf   # extracted text: aviles-2017-mc21-cobra-ie.txt
grounds:
  - netflow guide-tube-unheated treatment (base-case match)
  - P6 eigenvalue context
key-values:
  - value: 1.16424 (2.6e-5) MC21/COBRA-IE; 1.16361 VERA-CS; diff 63 pcm
    defines: P6 quarter-assembly eigenvalue (code solutions, not reference)
    status: verified
    locus: Table 2
  - value: +8.8 / -4.3 C, RMS 3.9 C
    defines: code-to-code agreement, local volume-averaged fuel pin temperature
    status: verified
    locus: sec. 4.2, Fig. 11
  - value: +0.8 / -1.5 C, RMS 0.5 C
    defines: code-to-code agreement, subchannel exit coolant temperature
    status: verified
    locus: sec. 4.2, Fig. 14
  - value: neighbor subchannels -1.5 C; guide-tube water +17 C (~50% of subchannel rise); +7 pcm
    defines: guide-tube heating sensitivity (base case = unheated guide tubes, as netflow models)
    status: verified
    locus: sec. 4.3
  - value: absolute P6 max volume-avg fuel temp & exit-coolant spread
    defines: published only in Figs. 11/14 (figure-derived, not stated in text)
    status: figure-derived
    locus: Figs. 11, 14
related: [[kelly-2017-mc21-ctf-vera]], [[godfrey-2014-vera-spec]]
---
Held (provided by the Body, 2026-05-20 — was `wanted`). The COBRA-IE companion to
[[kelly-2017-mc21-ctf-vera]]. Confirms the P6 eigenvalue and the volume-average
fuel-temperature definition, and grounds netflow's guide-tube-unheated treatment:
in the base case (guide tubes unheated, exactly as netflow models them) the guide
channels run cool; enabling guide-tube heating drops neighbor subchannels ~1.5 C
and raises guide-tube water ~17 C (~50% of the subchannel rise). Absolute P6 max
fuel temperature and exit-coolant spread remain figure-derived (Figs. 11/14).
