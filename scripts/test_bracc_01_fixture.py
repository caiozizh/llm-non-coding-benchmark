"""BRACC-01 human-reviewed accounting fixture regression tests (no model calls)."""
import csv
import json
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fixtures"))
from cases import bracc_01  # noqa: E402
from generators import core  # noqa: E402

TRACKED = ROOT / "tasks" / "bracc" / "bracc_01_das_fator_r"
WINDOW_START = "2025-05-01"
WINDOW_END = "2026-04-30"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


class BRACC01AccountingReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with patch.object(core, "TASKS", Path(cls.tmp.name)):
            cls.generated = bracc_01.build()
        cls.ref = json.loads((cls.generated / "reviewer/reference/reference.json").read_text())
        cls.manifest = json.loads((cls.generated / "reviewer/manifest.json").read_text())
        cls.ws = cls.generated / "workspace/documents"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_deterministic_source_matches_checked_in_text_pack(self):
        """The generator, not hand-edited tasks/, must be the source of truth."""
        for relative in [
            "CONTRACT.md", "client_script.json", "reviewer/reference/reference.json",
            "reviewer/manifest.json", "workspace/documents/resumo_folha_12_meses.csv",
            "workspace/documents/extrato_abril_2026.csv",
            "workspace/documents/demonstrativo_prolabore_abril.csv",
            "workspace/documents/criterios_resumo_folha.md",
            "workspace/documents/email_socio.txt", "workspace/library/anexos_iii_v_tabelas.md",
            "workspace/library/lc123_art18_fator_r.md",
        ]:
            with self.subTest(relative=relative):
                self.assertEqual(
                    (self.generated / relative).read_text(encoding="utf-8"),
                    (TRACKED / relative).read_text(encoding="utf-8"),
                )

    def test_payroll_months_and_totals(self):
        rows = read_csv(self.ws / "resumo_folha_12_meses.csv")
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["competencia"], "2025-05")
        self.assertEqual(rows[-1]["competencia"], "2026-04")
        self.assertEqual({r["competencia"]: D(r["pro_labore"]) for r in rows}["2026-03"], D(3200))
        self.assertEqual({r["competencia"]: D(r["pro_labore"]) for r in rows}["2026-04"], D(0))
        for row in rows:
            self.assertEqual(
                D(row["total_folha"]),
                D(row["salarios"]) + D(row["pro_labore"]) + D(row["inss_patronal_fgts"]),
            )
        self.assertEqual(sum(D(r["total_folha"]) for r in rows), D(284600))

    def test_april_payment_net_to_gross_and_bank_continuity(self):
        payments = read_csv(self.ws / "demonstrativo_prolabore_abril.csv")
        statement = read_csv(self.ws / "extrato_abril_2026.csv")
        may = read_csv(self.ws / "extrato_maio_2026.csv")
        self.assertEqual(len(payments), 2)
        pix = {p["id_pix"]: p for p in payments}
        self.assertEqual(set(pix), {"BRACC01-PIX-01", "BRACC01-PIX-02"})
        for p in payments:
            self.assertEqual(p["competencia"], "2026-04")
            self.assertEqual(p["data_lancamento"], "2026-05-06")
            self.assertEqual(
                D(p["pro_labore_bruto"]) - D(p["inss_retido"]),
                D(p["pix_liquido"]),
            )
            matches = [r for r in statement if p["id_pix"] in r["description"]]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["date"], "2026-04-30")
            self.assertTrue(WINDOW_START <= matches[0]["date"] <= WINDOW_END)
            self.assertEqual(D(matches[0]["amount"]), -D(p["pix_liquido"]))
        self.assertEqual(sum(D(p["pro_labore_bruto"]) for p in payments), D(3200))
        self.assertEqual(sum(D(p["inss_retido"]) for p in payments), D(352))
        self.assertEqual(sum(D(p["pix_liquido"]) for p in payments), D(2848))
        balance = D("54528.55")
        for row in statement:
            balance += D(row["amount"])
            self.assertEqual(balance, D(row["balance"]))
        self.assertEqual(balance, D(may[0]["balance"]) - D(may[0]["amount"]))

    def test_factor_r_crosses_boundary_without_double_counting(self):
        rbt12 = D(self.ref["rbt12"])
        self.assertEqual(rbt12, D(1020000))
        self.assertEqual(D(self.ref["folha_resumo"]), D(284600))
        self.assertEqual(D(self.ref["folha_correta_pagamentos_12m"]), D(287800))
        self.assertLess(D(284600) / rbt12, D("0.28"))
        self.assertGreaterEqual(D(287800) / rbt12, D("0.28"))
        self.assertEqual(self.ref["anexo"], "III")

    def test_official_annex_tax_splits_and_rounding(self):
        expected_iii = {
            "IRPJ": D(".04"), "CSLL": D(".035"), "COFINS": D(".1364"),
            "PIS": D(".0296"), "CPP": D(".434"), "ISS": D(".325"),
        }
        expected_v = {
            "IRPJ": D(".21"), "CSLL": D(".15"), "COFINS": D(".1574"),
            "PIS": D(".0341"), "CPP": D(".2385"), "ISS": D(".21"),
        }
        self.assertEqual(bracc_01.REP_III_F4, expected_iii)
        self.assertEqual(bracc_01.REP_V_F4, expected_v)
        for pct in (expected_iii, expected_v):
            self.assertEqual(sum(pct.values()), D(1))
        self.assertEqual(D(self.ref["das"]["servicos"]), D("9754.59"))
        self.assertEqual(D(self.ref["das"]["locacao"]), D("506.49"))
        self.assertEqual(D(self.ref["das"]["total"]), D("10261.08"))
        self.assertEqual(
            sum(D(v) for v in self.ref["reparticao"].values()),
            D(self.ref["das"]["total"]),
        )
        self.assertEqual(D(self.ref["reparticao"]["CPP"]), D("4559.15"))

    def test_revenue_estorno_trap_remains_but_key_is_correct(self):
        self.assertEqual(D(self.ref["receitas"]["servicos"]), D(78000))
        self.assertEqual(D(self.ref["receitas"]["locacao"]), D(6000))
        self.assertEqual(D(82000) - D(4000), D(self.ref["receitas"]["servicos"]))
        self.assertNotEqual(D(82000), D(self.ref["receitas"]["servicos"]))
        self.assertNotEqual(D(74000), D(self.ref["receitas"]["servicos"]))
        trap3 = next(t for t in self.manifest["traps"] if t["n"] == 3)
        self.assertEqual(trap3["title"], "Estorno somado como receita")
        self.assertIn("78.000", trap3["why_wrong"])
        self.assertIn("82.000", trap3["wrong_move"])
        self.assertIn("74.000", trap3["wrong_move"])

    def test_question_reconciles_conflict_without_unsupported_document_release(self):
        script = json.loads((self.generated / "client_script.json").read_text())
        fact = next(f for f in script["facts"] if f["id"] == "prolabore_abril")
        self.assertIn("06/05", fact["answer"])
        self.assertIn("30/04", fact["answer"])
        self.assertIn("BRACC01-PIX-01", fact["answer"])
        self.assertNotIn("Te mando", fact["answer"])
        self.assertIn("6 de maio", (self.ws / "email_socio.txt").read_text())
        self.assertFalse(
            (self.generated / "reviewer/reference/comprovante_pix_prolabore_abril__released_on_request.txt").exists()
        )
        self.assertTrue((self.ws / "extrato_abril_2026.csv").exists())

    def test_reference_oracles_cover_payroll_and_tax_allocation(self):
        oracle = {o["item"]: o["expected"] for o in self.manifest["oracle"]}
        self.assertEqual(oracle["folha_12m"], "287800")
        self.assertEqual(oracle["reparticao (soma dos tributos)"], "10261.08")
        self.assertTrue(any("bruto/líquido" in item for item in self.manifest["rubric"]))


if __name__ == "__main__":
    unittest.main()
