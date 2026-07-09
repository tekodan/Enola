"""Unit tests for the reliability report (Regla 1 — Valores Perdidos)."""

from src.report.reliability import calcular_valores_perdidos


def _row(**kw):
    base = {
        "id": 1,
        "tiene_violencia": "false",
        "categoria": "ninguna",
        "exclusion_label": None,
        "exclusion_codigo": None,
    }
    base.update(kw)
    return base


class TestCalcularValoresPerdidos:
    """Alerts and breakdown of the missing-values report."""

    def test_empty_input(self):
        r = calcular_valores_perdidos([])
        assert r.total == 0
        assert r.nivel == "ok"
        assert r.pct_basura == 0.0

    def test_no_basura_ok_level(self):
        rows = [_row(id=i) for i in range(100)]
        r = calcular_valores_perdidos(rows)
        assert r.n_basura_digital == 0
        assert r.pct_basura == 0.0
        assert r.nivel == "ok"
        assert "OK" in r.mensaje

    def test_below_5pct_ok_level(self):
        rows = [_row(id=i) for i in range(100)]
        # 3% CODIGO_99
        for i in range(3):
            rows[i]["exclusion_label"] = "CODIGO_99"
            rows[i]["exclusion_codigo"] = "COND_1_VACIO"
        r = calcular_valores_perdidos(rows)
        assert r.n_basura_digital == 3
        assert r.pct_basura == 3.0
        assert r.nivel == "ok"

    def test_between_5_and_10_warning(self):
        rows = [_row(id=i) for i in range(100)]
        for i in range(7):
            rows[i]["exclusion_label"] = "CODIGO_99"
        r = calcular_valores_perdidos(rows)
        assert r.pct_basura == 7.0
        assert r.nivel == "preventiva"
        assert "preventiva" in r.mensaje.lower()

    def test_above_10_critical(self):
        rows = [_row(id=i) for i in range(100)]
        for i in range(15):
            rows[i]["exclusion_label"] = "CODIGO_99"
        r = calcular_valores_perdidos(rows)
        assert r.pct_basura == 15.0
        assert r.nivel == "critica"
        assert "CRÍTICA" in r.mensaje or "CR\u00cdTICA" in r.mensaje

    def test_violencia_comun_separated(self):
        """VIOLENCIA_COMUN rows are counted but don't trigger alerts."""
        rows = [_row(id=i) for i in range(100)]
        for i in range(20):
            rows[i]["exclusion_label"] = "VIOLENCIA_COMUN"
        r = calcular_valores_perdidos(rows)
        assert r.n_violencia_comun == 20
        assert r.pct_violencia_comun == 20.0
        assert r.pct_basura == 0.0
        assert r.nivel == "ok"

    def test_detalle_basura_codigos_breakdown(self):
        rows = [_row(id=i) for i in range(10)]
        rows[0]["exclusion_label"] = "CODIGO_99"
        rows[0]["exclusion_codigo"] = "COND_1_VACIO"
        rows[1]["exclusion_label"] = "CODIGO_99"
        rows[1]["exclusion_codigo"] = "COND_2_ENLACE_HUERFANO"
        rows[2]["exclusion_label"] = "CODIGO_99"
        rows[2]["exclusion_codigo"] = "COND_2_ENLACE_HUERFANO"
        rows[3]["exclusion_label"] = "CODIGO_99"
        rows[3]["exclusion_codigo"] = "COND_3_RUIDO_TIPOGRAFICO"
        r = calcular_valores_perdidos(rows)
        assert r.n_basura_digital == 4
        assert r.detalle_basura_codigos["COND_1_VACIO"] == 1
        assert r.detalle_basura_codigos["COND_2_ENLACE_HUERFANO"] == 2
        assert r.detalle_basura_codigos["COND_3_RUIDO_TIPOGRAFICO"] == 1

    def test_to_dict_round_trip(self):
        rows = [_row(id=i) for i in range(10)]
        r = calcular_valores_perdidos(rows)
        d = r.to_dict()
        assert d["total"] == 10
        assert d["nivel"] in {"ok", "preventiva", "critica"}
        assert "mensaje" in d

    def test_boundary_at_5_excludes_5(self):
        """Exactly 5% stays OK (the alert triggers only when strictly >5)."""
        rows = [_row(id=i) for i in range(100)]
        for i in range(5):
            rows[i]["exclusion_label"] = "CODIGO_99"
        r = calcular_valores_perdidos(rows)
        assert r.nivel == "ok"

    def test_boundary_at_10_excludes_10(self):
        """Exactly 10% stays 'preventiva' (the alert triggers only when strictly >10)."""
        rows = [_row(id=i) for i in range(100)]
        for i in range(10):
            rows[i]["exclusion_label"] = "CODIGO_99"
        r = calcular_valores_perdidos(rows)
        assert r.nivel == "preventiva"

    def test_boundary_just_over_10(self):
        rows = [_row(id=i) for i in range(100)]
        for i in range(11):
            rows[i]["exclusion_label"] = "CODIGO_99"
        r = calcular_valores_perdidos(rows)
        assert r.nivel == "critica"
