# Reference Repository — netflow

Local copies of sources that ground this project's results, per
`Soul-System/operations/reference-repository.md`. A claim that touches the
Universe cites a saved source here, not a memory.

Bibliographic core (CSL-JSON, exportable): `references.json`.
Provenance + extracted values: the per-document `<id>.md` sidecars.

## Netflow-relevant measured fuel-temperature data (the actionable path)

Single-rod measured fuel-centerline-temperature data — the quantity netflow's
fuel-pin model computes, and the route from "code comparison" to real validation.

- [frapcon-ifa432-ornl-tm-2012-195](frapcon-ifa432-ornl-tm-2012-195.md) — **HELD**. ORNL/TM-2012/195; IFA-432 rods 1/2/3/5 measured centerline T vs LHGR (figures). *(public)*
- ifa432-final-data-report — primary measured-data report; **OSTI 5293733**. *(public; not yet downloaded)*
- ifpe-ifa432-nea1488 — IFPE curated tabulated dataset; **NEA-1488** (OECD-NEA Data Bank). *(NEA-member request — for you to pull)*
- pnnl-19418-frapcon-integral-assessment — tabulated measured-vs-predicted; **PNNL-19418 Vol.2 Rev.2 / NRC ML16118A434**. *(public)*
- iaea-tecdoc-1697-fuel-behaviour — FUMEX-III benchmark cases; **IAEA-TECDOC-1697**. *(public, IAEA)*

## Held (document on disk)

- [godfrey-2014-vera-spec](godfrey-2014-vera-spec.md) — VERA spec; geometry, statepoint, "no reference solution for P6/P7." — **grounds netflow**
- [kelly-2017-mc21-ctf-vera](kelly-2017-mc21-ctf-vera.md) — MC21/CTF; fuel temp 1065.8 °C, spread 6.6/8.7 K. — **grounds netflow**
- [aviles-2017-mc21-cobra-ie](aviles-2017-mc21-cobra-ie.md) — MC21/COBRA-IE; P6 eigenvalue + guide-tube sensitivity. — **grounds netflow**
- [frapcon-ifa432-ornl-tm-2012-195](frapcon-ifa432-ornl-tm-2012-195.md) — IFA-432 measured fuel-T (see above). — **netflow-relevant**
- [kim-2023-wbn1-polaris-parcs](kim-2023-wbn1-polaris-parcs.md) — WBN1/BEAVRS conf. paper. — context
- [kim-2024-wbn1-cycles-1-3](kim-2024-wbn1-cycles-1-3.md) — WBN1 Cycles 1-3 report; measured boron/ITC. — context
- [collins-2020-beavrs-vera](collins-2020-beavrs-vera.md) — VERA vs MIT BEAVRS measured. — context

## Identified — file not retrieved

- [palmtag-2013-vera-p6-coupled](palmtag-2013-vera-p6-coupled.md) — P6 absolute results; casl 404. *(wanted, netflow-useful)*
- [gehin-2013-wbn1-zppt](gehin-2013-wbn1-zppt.md) — measured WBN1 ZPPT; OSTI ~46 MB. *(context)*
- casl-2015-wbn1-cycles-1-12 (CASL-U-2015-0206-000) · casl-2016-bison-fuel-temp (CASL-U-2016-1059-000). *(context / lead)*

## Status of the scope question

The earlier bottleneck — every measured reference being full-core, which netflow
can't reproduce — is **resolved in principle**: the IFA-432 single-rod measured
centerline-temperature data IS netflow-reproducible. Doing that comparison would
be netflow's first genuine *validation* (vs measured), not a code comparison. The
cleanest raw data is the IFPE dataset (NEA-1488), which needs NEA-member access.
