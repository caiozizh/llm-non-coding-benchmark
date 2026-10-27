"""BRACC-1 · L1 · DAS do Simples com Fator R na fronteira — 'é Anexo V, serviço de TI'."""
import datetime as dt
from decimal import Decimal as D, ROUND_DOWN
from generators.core import Case, bank_statement, nfe_xml, money, q2, COMMON_RULES

ANO = 2026
# Anexo III (LC 123, redação LC 155/2016): faixa 4 (720.000,01–1.800.000): 16% PD 35.640; repartição IRPJ 4, CSLL 3,5, COFINS 13,64, PIS 2,96, CPP 43,40, ISS 32,5
ANEXO_III = [(D("180000"), D("0.06"), D("0")), (D("360000"), D("0.112"), D("9360")), (D("720000"), D("0.135"), D("17640")), (D("1800000"), D("0.16"), D("35640")), (D("3600000"), D("0.21"), D("125640")), (D("4800000"), D("0.33"), D("648000"))]
ANEXO_V = [(D("180000"), D("0.155"), D("0")), (D("360000"), D("0.18"), D("4500")), (D("720000"), D("0.195"), D("9900")), (D("1800000"), D("0.205"), D("17100")), (D("3600000"), D("0.23"), D("62100")), (D("4800000"), D("0.305"), D("540000"))]
REP_III_F4 = {"IRPJ": D("0.04"), "CSLL": D("0.035"), "COFINS": D("0.1364"), "PIS": D("0.0296"), "CPP": D("0.434"), "ISS": D("0.325")}
REP_V_F4 = {"IRPJ": D("0.21"), "CSLL": D("0.15"), "COFINS": D("0.1574"), "PIS": D("0.0341"), "CPP": D("0.2385"), "ISS": D("0.21")}


def efetiva(rbt12, tabela):
    for teto, aliq, pd in tabela:
        if rbt12 <= teto:
            return (rbt12 * aliq - pd) / rbt12, aliq, pd
    raise ValueError

def distribuir_centavos(valor, percentuais):
    """Aloca centavos por maiores restos, mantendo a partilha igual ao total do DAS."""
    assert sum(percentuais.values()) == D("1"), percentuais
    bruto = {k: valor * peso for k, peso in percentuais.items()}
    base = {k: v.quantize(D("0.01"), rounding=ROUND_DOWN) for k, v in bruto.items()}
    faltantes = int((valor - sum(base.values())) / D("0.01"))
    ordem = list(percentuais)
    for k in sorted(ordem, key=lambda k: (-(bruto[k] - base[k]), ordem.index(k)))[:faltantes]:
        base[k] += D("0.01")
    assert sum(base.values()) == valor
    return base


def build():
    c = Case("bracc_01_das_fator_r", "bracc", "Apuração do DAS com Fator R na fronteira", "L1", cur="BRL")
    emit = {"cnpj": "41.228.907/0001-55".replace(".", "").replace("/", "").replace("-", ""), "nome": "LUMEN SOLUCOES DIGITAIS LTDA ME", "crt": "1"}
    # faturamento 12 meses anteriores (mai/2025–abr/2026)
    fat = [D(x) for x in ("78000", "81500", "84000", "86000", "79500", "90000", "88000", "92000", "85000", "83000", "86000", "87000")]
    rbt12 = sum(fat)  # 1.020.000
    # folha 12 meses conforme RESUMO (com omissão do pró-labore de abril de R$ 3.200)
    folha_resumo = [D(x) for x in ("23400", "23400", "23800", "23800", "23800", "24100", "24100", "24100", "24300", "24300", "24100", "21400")]  # abr = 21.400 (pró-labore ainda não registrado)
    folha_real = list(folha_resumo); folha_real[11] += D("3200")
    fr_resumo = sum(folha_resumo) / rbt12
    fr_real = sum(folha_real) / rbt12
    assert fr_resumo < D("0.28") <= fr_real, (fr_resumo, fr_real)
    # receitas de maio/2026
    servicos = [("NFS-e 1181", "Desenvolvimento de software — sprint 11", D("18000")), ("NFS-e 1182", "Sustentação mensal — Cliente Orla", D("12500")), ("NFS-e 1183", "Consultoria de arquitetura", D("9800")),
                ("NFS-e 1184", "Desenvolvimento — módulo fiscal", D("22000")), ("NFS-e 1185", "Suporte técnico", D("6700")), ("NFS-e 1186", "Treinamento equipe", D("4500")), ("NFS-e 1187", "Desenvolvimento — integração", D("8500"))]
    estorno = ("NFS-e 1188 (SUBSTITUI/CANCELA parcialmente 1184)", "Estorno parcial — glosa de escopo acordada", D("-4000"))
    locacao = ("NF-e 000.512", "Locação de 20 notebooks — maio", D("6000"))
    rec_serv = sum(x[2] for x in servicos) + estorno[2]  # 82.000 - 4.000 = 78.000
    rec_loc = locacao[2]
    ef3, aliq3, pd3 = efetiva(rbt12, ANEXO_III)
    ef5, aliq5, pd5 = efetiva(rbt12, ANEXO_V)
    das_serv = q2(rec_serv * ef3)
    das_loc = q2(rec_loc * ef3 * (1 - REP_III_F4["ISS"]))   # locação de bens móveis: sem ISS (SV 31)
    das = das_serv + das_loc
    das_errado_v_nominal = q2((rec_serv + rec_loc + D("4000")) * aliq5)  # anexo V, nominal, sem estorno
    reparticao_serv = distribuir_centavos(das_serv, REP_III_F4)
    reparticao_loc = distribuir_centavos(
        das_loc, {k: v / (1 - REP_III_F4["ISS"]) for k, v in REP_III_F4.items() if k != "ISS"}
    )
    reparticao = {k: reparticao_serv[k] + reparticao_loc.get(k, D("0")) for k in REP_III_F4}
    assert sum(reparticao.values()) == das

    # ---- documentos
    c.csv("faturamento_12_meses.csv", ["competencia", "receita_bruta"], [[f"{(dt.date(2025, 5, 1) + dt.timedelta(days=31*i)).strftime('%Y-%m')}", str(v)] for i, v in enumerate(fat)])
    meses = ["2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04"]
    c.csv("resumo_folha_12_meses.csv", ["competencia", "salarios", "pro_labore", "inss_patronal_fgts", "total_folha", "obs"],
          [[m, str(v - D("4700") - (D("3200") if i != 11 else D("0"))), "3200" if i != 11 else "0",
            "4700", str(v), "" if i != 11 else "Pró-labore de abril ainda não lançado no fechamento das 16h de 30/04"]
           for i, (m, v) in enumerate(zip(meses, folha_resumo))])
    c.doc("criterios_resumo_folha.md", """
# Resumo gerencial da folha — critério e data de extração

Exportado em 30/04/2026 às 16h, antes do encerramento bancário do dia.
A coluna chamada `competencia` pelo sistema agrupa **mês de pagamento ou recolhimento**,
não necessariamente o mês de competência trabalhista. Somente os valores pagos
e recolhidos na janela maio/2025 a abril/2026 integram este relatório.

`salarios` e `pro_labore`: remuneração **bruta paga** conforme folha/eSocial.
`inss_patronal_fgts`: contribuição previdenciária patronal e FGTS efetivamente recolhidos
no mês (não inclui o INSS retido dos trabalhadores ou sócios).
O pagamento líquido que consta do banco pode diferir da remuneração bruta registrada.
Conferir eventuais pagamentos feitos após o horário da extração.
""")
    # O extrato de abril é uma evidência visível desde o início, não uma falsa
    # promessa de entrega dinâmica pelo cliente; encerra com o saldo inicial de maio.
    c.csv("extrato_abril_2026.csv", ["date", "description", "amount", "balance"], [
        ["2026-04-03", "PIX RECEBIDO CLIENTE ORLA", "11000.00", "65528.55"],
        ["2026-04-07", "SALARIOS LIQUIDOS - COMP MAR/2026", "-15000.00", "50528.55"],
        ["2026-04-20", "CPP E FGTS RECOLHIDOS - COMP MAR/2026", "-4700.00", "45828.55"],
        ["2026-04-25", "INSS RETIDO SALARIOS - COMP MAR/2026", "-1700.00", "44128.55"],
        ["2026-04-30", "PIX PRO-LABORE ABR RENATO - ID BRACC01-PIX-01", "-1424.00", "42704.55"],
        ["2026-04-30", "PIX PRO-LABORE ABR JULIA - ID BRACC01-PIX-02", "-1424.00", "41280.55"],
    ])
    c.csv("demonstrativo_prolabore_abril.csv",
          ["competencia", "beneficiario", "pro_labore_bruto", "inss_retido", "pix_liquido", "id_pix", "data_lancamento"],
          [["2026-04", "Renato Lima", "1600.00", "176.00", "1424.00", "BRACC01-PIX-01", "2026-05-06"],
           ["2026-04", "Julia Martins", "1600.00", "176.00", "1424.00", "BRACC01-PIX-02", "2026-05-06"]])
    rows = []
    for d, desc, amt in [(2, "PIX RECEBIDO ORLA TECNOLOGIA", 12500), (5, "TED RECEBIDA BANCO SAFRA — CLIENTE", 18000), (7, "FOLHA MAIO — SALARIOS", -16600), (7, "DARF/GPS/FGTS ABR", -4700), (9, "PIX RECEBIDO", 9800), (12, "ALUGUEL ESCRITORIO", -4200), (15, "TED RECEBIDA — MODULO FISCAL", 22000),
                        (16, "PIX ENVIADO PRO-LABORE MAI — RENATO", -1600), (16, "PIX ENVIADO PRO-LABORE MAI — JULIA", -1600), (19, "PIX RECEBIDO SUPORTE", 6700), (20, "DAS ABR/2026", -10480.22), (22, "PIX RECEBIDO TREINAMENTO", 4500),
                        (26, "TED RECEBIDA LOCACAO NOTEBOOKS", 6000), (28, "PIX RECEBIDO INTEGRACAO", 8500), (29, "PIX ENVIADO ESTORNO GLOSA — CLIENTE 1184", -4000)]:
        rows.append((dt.date(ANO, 5, d), desc, D(str(amt))))
    bank_statement(c, "extrato_maio_2026.pdf", bank="Banco Meridional S.A.", holder="LUMEN SOLUCOES DIGITAIS LTDA ME", address="Rua Haddock Lobo 585 cj 41, São Paulo SP", account_last4="3302-7", period="01/05/2026 – 31/05/2026", opening=D("41280.55"), rows=rows, cur="BRL")
    notas_md = "# Notas emitidas — maio/2026\n\n| Documento | Descrição | Valor |\n|---|---|---:|\n" + "\n".join(f"| {n} | {d} | {money(v, 'BRL')} |" for n, d, v in servicos + [estorno, locacao]) + f"\n\n*Total serviços (bruto): {money(sum(x[2] for x in servicos), 'BRL')} · estorno {money(estorno[2], 'BRL')} · locação {money(rec_loc, 'BRL')}*"
    c.doc("notas_emitidas_maio.md", notas_md)
    nfe_xml(c, "nfe_000512_locacao.xml", numero=512, serie=1, emissao=dt.date(ANO, 5, 26), emit=emit, dest={"cnpj": "08334411000190", "nome": "ORLA TECNOLOGIA LTDA"}, itens=[{"descr": "Locação de notebooks (20 un.) — maio/2026", "ncm": "00000000", "qtd": 1, "vun": 6000}], cfop="5949", natureza="Locação de bens móveis")
    c.doc("email_socio.txt", """
De: Renato Lima <renato@lumen.dev>
Assunto: DAS de maio

Oi — segue o resumo da folha e as notas. Ano passado a gente pagava pelo Anexo V (TI), é só repetir o
cálculo da tabela com a alíquota da faixa. O pró-labore de abril está anotado aqui como pago em 6 de maio, se
isso importar. Ah, e teve uma nota de locação de notebooks — acho que vai junto com os serviços.
""")
    # ---- biblioteca
    c.library("lc123_art18_fator_r.md", "LC 123/2006, art. 18 — alíquota efetiva e Fator R (excertos)", "LC 123/2006, art. 18, §§1º, 1º-A, 5º-J, 5º-K, 5º-M; Resolução CGSN 140/2018, arts. 25, 26", """
**§1º** Para efeito de determinação da alíquota nominal, o sujeito passivo utilizará a **receita bruta acumulada nos doze meses anteriores** ao do período de apuração (RBT12).
**§1º-A** A **alíquota efetiva** é o resultado de: **(RBT12 × Aliq − PD) / RBT12**, em que Aliq é a alíquota nominal da faixa e PD a parcela a deduzir.
**§5º-J / §5º-M (Fator R).** As atividades de prestação de serviços de TI (desenvolvimento, licenciamento, suporte etc.), entre outras, serão tributadas pelo **Anexo III quando a razão entre a folha de salários (incluídos encargos, pró-labore e FGTS) e a receita bruta, ambos dos 12 meses anteriores, for igual ou superior a 28%**; caso contrário, pelo **Anexo V**.
**Resolução CGSN 140, art. 26, §§1º-2º (síntese não literal).** Consideram-se remunerações **brutas efetivamente pagas** nos 12 meses anteriores e contribuição patronal e FGTS efetivamente recolhidos. O §2º trata das remunerações informadas ao Fisco. Não confundir competência da folha com data de pagamento para a FS12; conciliar folha, pagamentos e recolhimentos.
**Segregação de receitas (art. 18, §4º).** O contribuinte deve segregar as receitas por atividade (serviços, locação de bens móveis, comércio etc.) e aplicar a cada uma o anexo e a alíquota correspondentes.
**Devoluções/cancelamentos.** Não integram a receita bruta as vendas canceladas e os descontos incondicionais; o cancelamento/estorno de serviço reduz a receita do mês em que ocorrer.
""", verbatim=False, note="Verificar redação exata; percentuais do Fator R e definição de folha conforme Res. CGSN 140.")
    c.library("anexos_iii_v_tabelas.md", "Anexos III e V da LC 123/2006 — tabelas vigentes", "LC 123/2006, Anexos III e V (redação LC 155/2016)", """
**Anexo III (serviços)**

| Faixa | RBT12 até | Alíquota | Parcela a deduzir |
|---|---:|---:|---:|
| 1 | 180.000,00 | 6,00% | — |
| 2 | 360.000,00 | 11,20% | 9.360,00 |
| 3 | 720.000,00 | 13,50% | 17.640,00 |
| 4 | 1.800.000,00 | 16,00% | 35.640,00 |
| 5 | 3.600.000,00 | 21,00% | 125.640,00 |
| 6 | 4.800.000,00 | 33,00% | 648.000,00 |

Repartição, 4ª faixa: IRPJ 4,00% · CSLL 3,50% · COFINS 13,64% · PIS 2,96% · CPP 43,40% · **ISS 32,50%**.

**Anexo V (serviços — Fator R < 28%)**

| Faixa | RBT12 até | Alíquota | Parcela a deduzir |
|---|---:|---:|---:|
| 1 | 180.000,00 | 15,50% | — |
| 2 | 360.000,00 | 18,00% | 4.500,00 |
| 3 | 720.000,00 | 19,50% | 9.900,00 |
| 4 | 1.800.000,00 | 20,50% | 17.100,00 |
| 5 | 3.600.000,00 | 23,00% | 62.100,00 |
| 6 | 4.800.000,00 | 30,50% | 540.000,00 |

Repartição, 4ª faixa: IRPJ 21,00% · CSLL 15,00% · COFINS 15,74% · PIS 3,41% · CPP 23,85% · ISS 21,00%.

Os percentuais de repartição são frações do DAS, não alíquotas diretas sobre a receita. Na locação de bens móveis, desconta-se a fração de ISS da alíquota efetiva do Anexo III.
""", verbatim=True)
    c.library("locacao_bens_moveis_iss.md", "Locação de bens móveis no Simples — sem ISS", "LC 123/2006, art. 18, §5º-A; Súmula Vinculante 31 (STF); Res. CGSN 140, art. 25, §1º, V", "As atividades de **locação de bens móveis** são tributadas na forma do **Anexo III, deduzida a parcela correspondente ao ISS**, porque a locação de bens móveis não é serviço para fins de ISS (Súmula Vinculante 31: 'É inconstitucional a incidência do ISS sobre operações de locação de bens móveis').", verbatim=False)
    c.contract(f"""
# Engajamento: apuração do DAS de maio/{ANO} — Lumen Soluções Digitais ME

Apure o DAS de maio a partir das notas, extratos de abril/maio, demonstrativo de pró-labore, resumo de folha e faturamento dos 12
meses anteriores. O sócio pede para "repetir o Anexo V com a alíquota da faixa". Use apenas a biblioteca.

## Entregáveis (em `workspace/deliverable/`)
1. `apuracao.json` — `{{"rbt12": 0, "folha_12m": 0, "fator_r": 0.0, "anexo": "III|V", "faixa": 0, "aliquota_nominal": 0.0, "parcela_deduzir": 0, "aliquota_efetiva": 0.0, "receitas": {{"servicos": 0, "locacao": 0}}, "das": {{"servicos": 0, "locacao": 0, "total": 0}}, "reparticao": {{"IRPJ": 0, "CSLL": 0, "COFINS": 0, "PIS": 0, "CPP": 0, "ISS": 0}}}}`
2. `memoria.md` — a memória de cálculo com cada fonte da biblioteca; classificação de cada nota; o que foi feito com o estorno e com a locação.
3. `PERGUNTAS.md` (opcional) e `STATUS.md`.
{COMMON_RULES}
""")
    c.client_script("Renato Lima, sócio-administrador; prático; quer pagar o DAS logo.", [
        {"id": "prolabore_abril", "trigger": ["pró-labore de abril", "pro-labore abr", "abril", "em aberto", "3.200", "3200", "extrato", "pagamento"], "answer": "Conferi com o financeiro: minha mensagem dizia 06/05, mas essa foi a data do lançamento no sistema. Os pagamentos foram em 30/04 às 17h52/17h53, conforme o extrato de abril, IDs BRACC01-PIX-01 e BRACC01-PIX-02. Cada pró-labore era R$ 1.600 BRUTOS, com INSS retido de R$ 176 e Pix líquido de R$ 1.424. O resumo de folha foi exportado antes dos Pix, às 16h de 30/04, e ainda não incluía o pró-labore de abril. O demonstrativo de pró-labore foi lançado em 06/05.", "if_not_asked": "must_flag"},
        {"id": "estorno", "trigger": ["estorno", "1188", "glosa", "cancelamento"], "answer": "O cliente contestou parte do escopo da 1184; a gente emitiu a 1188 estornando R$ 4.000 e devolveu via PIX.", "if_not_asked": "none"},
        {"id": "locacao", "trigger": ["locação", "notebooks", "512"], "answer": "Alugamos 20 notebooks pra Orla por uns meses. Emiti NF-e porque me disseram que locação não é NFS-e.", "if_not_asked": "none"},
    ])
    ref = {"rbt12": rbt12, "folha_resumo": sum(folha_resumo), "folha_correta_pagamentos_12m": sum(folha_real), "fator_r_resumo": q2(fr_resumo * 100), "fator_r_correto": q2(fr_real * 100),
           "anexo": "III", "faixa": 4, "aliquota_nominal": aliq3, "parcela_deduzir": pd3, "aliquota_efetiva_pct": q2(ef3 * 100 * 10000) / 10000,
           "receitas": {"servicos": rec_serv, "locacao": rec_loc}, "das": {"servicos": das_serv, "locacao": das_loc, "total": das}, "reparticao": reparticao,
           "caminho_errado": {"anexo_v_nominal_sem_estorno": das_errado_v_nominal,
                             "anexo_v_efetiva": q2((rec_serv + rec_loc) * ef5),
                             "anexo_v_servicos_locacao_correta": q2(rec_serv * ef5) + das_loc},
           "nota": "FS12 (maio/2025 a abril/2026): resumo gerencial de pagamentos R$ 284.600 exportado em 30/04 às 16h; inclui março R$ 3.200, mas omite abril R$ 3.200. Extrato de abril: dois Pix líquidos de R$ 1.424 em 30/04 com IDs conciliados ao demonstrativo de pró-labore bruto (R$ 1.600 cada; INSS retido R$ 176 cada), registrado apenas 06/05. O e-mail diz 06/05 como suposta data de pagamento; o script esclarece que foi a data de lançamento. FS12 R$ 287.800; Anexo III; não somar Pix líquidos como remuneração bruta."}
    c.reference("reference.json", ref)
    c.note("BRACC-01 v1.2: relatório de folha, extrato de abril e demonstrativo de pró-labore conciliados. A divergência entre e-mail (06/05) e extrato (30/04) é proposital e resolvida por pergunta. Os dois documentos financeiros já estão no workspace; nenhum comprovante é prometido como liberação dinâmica.")
    c.trap(1, "Alíquota nominal em vez da efetiva", f"DAS = receita × 20,5% (ou × 16%)", f"Art. 18 §1º-A: efetiva = (RBT12×Aliq − PD)/RBT12 = {q2(ef3*100)}% no Anexo III", "Tabela; LC 123", "DAS errado (a maior)", "C", "LC 123 art. 18 §1º-A", "high")
    c.trap(2, "Anexo V por Fator R < 28% no resumo", f"Fator R {q2(fr_resumo*100)}% → Anexo V", f"O resumo exportado em 30/04 às 16h omite R$ 3.200 BRUTOS pagos às 17h52/17h53. O extrato registra R$ 2.848 líquidos e o demonstrativo explica R$ 352 de INSS retido; 06/05 foi data de lançamento, não de pagamento. FS12 {sum(folha_real)} → Fator R {q2(fr_real*100)}% → Anexo III. O modelo deve identificar e conciliar a divergência antes da conclusão, sem dupla contagem.", "resumo_folha_12_meses.csv; criterios_resumo_folha.md; extrato_abril_2026.csv; demonstrativo_prolabore_abril.csv; email_socio.txt; script do cliente", f"Escolha do Anexo V para serviços elevaria o DAS em {money(q2(rec_serv * ef5) + das_loc - das, 'BRL')}", "C", "LC 123 art. 18 §5º-J; Res. CGSN 140 art. 26", "high")
    c.trap(3, "Estorno somado como receita", "Receita de serviços 82.000 por ignorar estorno, ou 74.000 por descontá-lo duas vezes", "Serviços: 82.000 de notas positivas - 4.000 de estorno = 78.000; deduzir uma única vez", "NFS-e 1188; PIX de devolução", "DAS a maior", "M", "LC 123 art. 18 (receita bruta)", "high")
    c.trap(4, "Locação tributada com ISS", "Locação no Anexo III cheio (ou no V)", "Anexo III deduzida a parcela do ISS (SV 31): 32,5% da alíquota efetiva na 4ª faixa", "NF-e 512 (CFOP 5949, locação); biblioteca", "ISS indevido", "M", "LC 123 art. 18 §5º-A; SV 31", "high")
    c.oracle("das.total", str(das), "exact (±R$ 1)", "apuracao.json")
    c.oracle("folha_12m", str(sum(folha_real)), "exact", "apuracao.json; demonstrativo e extrato abril")
    c.oracle("reparticao (soma dos tributos)", str(das), "±R$ 0,01", "sum(apuracao.json.reparticao.values())")
    c.oracle("anexo", "III", "exact", "")
    c.oracle("aliquota_efetiva", f"{q2(ef3*100)}%", "±0,01 p.p.", "")
    c.oracle("receitas.servicos", str(rec_serv), "exact", "")
    c.oracle("das.locacao", str(das_loc), "±R$ 1", "")
    c.oracle("Se o pró-labore não foi perguntado: PERGUNTAS.md ou premissa explícita", "true", "exact", "")
    c.rubric("memoria.md explica o Fator R com a folha corrigida e cita a Res. CGSN 140 art. 26")
    c.rubric("memoria.md concilia e-mail de 06/05, extrato de 30/04 e valores bruto/líquido, sem duplicar pró-labore")
    return c.finish()
