# BRACC-01 — human-in-the-loop fixture repair (accounting evidence)

Scope: `bracc_01_das_fator_r` only. This note documents a synthetic case repair, not
a review or certification of any actual company's tax assessment.

## What was wrong in the original pack

The generated March 2026 payroll row showed R$ 0 pró-labore but incorrectly
referred to **April** being outstanding. The April row already included R$ 3,200,
while the keyed answer added another R$ 3,200. The email described payment on
May 6; the scripted response said April 30; an allegedly "released on request"
receipt lived only in reviewer-only files and was never delivered by the harness.
The fourth-band Anexo III tax allocation totaled 99.85%, and trap 3 named
R$ 74,000 as the correct service revenue although the actual reference and
oracle used R$ 78,000.

These fixture defects were previously flagged in the 2026-10-27 grading report.
The repair intentionally preserves the accounting traps while correcting their
supporting evidence and expected answers.

## Repaired evidence path

1. The 12-month management report aggregates **payment / remittance month**,
   despite the legacy `competencia` column name. Its April 30 export was taken
   at 16:00 and totals R$ 284,600, with March pró-labore correctly recorded and
   April pró-labore omitted.
2. The April bank CSV shows two **net** PIX payments of R$ 1,424 on April 30
   (17:52 and 17:53), with reconciliation identifiers; its ending balance
   matches the May statement's opening balance.
3. The remuneration statement reconciles each R$ 1,424 PIX to **R$ 1,600 gross**
   less R$ 176 retained INSS. Therefore April adds **R$ 3,200 gross** to FS12,
   not R$ 2,848 cash, and without double-counting.
4. The email still suggests payment on May 6. This is an **intentional question
   trigger**: the client clarifies that May 6 was the date the payroll transaction
   was posted to the accounting system. All evidence needed for verification is
   actually present in the candidate's initial workspace; the controller does not
   promise a nonexistent dynamically released attachment.
5. The corrected FS12 is R$ 287,800 (from R$ 284,600), RBT12 is
   R$ 1,020,000, and Factor R moves from 27.90% to 28.22%, crossing the 28%
   boundary. The services qualify for Anexo III under the synthetic assumptions.

**Service revenue trap remains intentional:** seven service invoices total
R$ 82,000, the cancellation is R$ 4,000, and correct net service revenue is
R$ 78,000. Ignoring the cancellation yields R$ 82,000; deducting twice yields
R$ 74,000. Rental of movable goods (R$ 6,000) is segregated under Anexo III
with its ISS allocation excluded.

## Deterministic expected values

| Field | Value |
|---|---:|
| RBT12 | R$ 1,020,000.00 |
| FS12, pre-reconciliation | R$ 284,600.00 |
| FS12, reconciled | R$ 287,800.00 |
| Factor R | 28.22% |
| Annex for subject services | III, band 4 |
| Net service revenue | R$ 78,000.00 |
| Rental revenue | R$ 6,000.00 |
| Service DAS | R$ 9,754.59 |
| Rental DAS (without ISS) | R$ 506.49 |
| **Total DAS** | **R$ 10,261.08** |

Anexo III fourth-band distribution: IRPJ 4%, CSLL 3.50%, COFINS 13.64%,
PIS/Pasep 2.96%, CPP 43.40%, ISS 32.50%. The reference uses a deterministic
largest-remainder cent allocation so the six tax components add up to the DAS
without rounding leakage. Anexo V fourth-band percentages are also included
in the candidate library for appropriately conditional calculations.

## Validation and reproducibility

Source of truth: `fixtures/cases/bracc_01.py`; `tasks/` contains generated
artifacts. After installing the dependencies described in the root README:

```bash
python3 scripts/build_cases.py --only bracc_01
python3 scripts/check_pack.py
python3 -m unittest discover -s scripts -p 'test_bracc_01_fixture.py'
```

Regression tests check the regenerated case against checked-in text artifacts,
payment-window inclusion, gross-to-net reconciliation, no payroll duplication,
bank statement continuity, tax distributions, intended revenue trap and oracle.

**Benchmark versioning:** results under `results/` were obtained with the
older fixture. This repair must be evaluated as a new case revision, with new
candidate runs and blinded grading, not retroactively substituted into the
published 2026-10-27 scores. The broader proposed dimension of professional
judgment / evidence reconciliation belongs in a separate methodological PR.

## Official reference sources

- [LC 123/2006, art. 18 and Anexos III/V (Câmara dos Deputados)](https://www2.camara.leg.br/legin/fed/leicom/2006/leicomplementar-123-14-dezembro-2006-548099-normaatualizada-pl.html)
- [Resolução CGSN 140/2018, art. 26 (Receita Federal)](https://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idAto=92278)
