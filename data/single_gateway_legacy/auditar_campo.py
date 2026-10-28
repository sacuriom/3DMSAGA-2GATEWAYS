"""Recalcula evidencia archivada de campo sin leer exportaciones con credenciales.

Ejecutar: python datos_campo/auditar_campo.py
Solo escribe los resúmenes derivados dentro de datos_campo/.
La reconstrucción de RF verifica el predictor utilizado, no su exactitud física.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
INPUT = BASE / "fuentes"


def read(name):
    with (INPUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def metrics(rows):
    pairs = []
    for row in rows:
        try:
            theoretical = float(row["RSSI_Teorico_dBm"])
            empirical = float(row["RSSI_Empirico_dBm"])
        except (KeyError, ValueError):
            continue
        if math.isfinite(theoretical) and math.isfinite(empirical):
            pairs.append((theoretical, empirical))
    if not pairs:
        return {"n_rssi": 0}
    x, y = zip(*pairs)
    error = [b - a for a, b in pairs]
    mx, my = statistics.mean(x), statistics.mean(y)
    denominator = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    r = sum((a - mx) * (b - my) for a, b in pairs) / denominator if denominator else None
    return {
        "n_rssi": len(pairs),
        "rmse_db": math.sqrt(statistics.mean(e * e for e in error)),
        "mae_db": statistics.mean(abs(e) for e in error),
        "bias_emp_menos_teo_db": statistics.mean(error),
        "sd_error_poblacional_db": statistics.pstdev(error),
        "similitud_6db_pct": 100 * sum(abs(e) <= 6 for e in error) / len(error),
        "similitud_10db_pct": 100 * sum(abs(e) <= 10 for e in error) / len(error),
        "pearson_r": r,
        "pearson_r_cuadrado": r * r if r is not None else None,
    }


def rf(row, height, haversine):
    lat, lon = float(row["Lat"]), float(row["Lon"])
    alt = float(row["Altitud_m"])
    radius = 6371000.0
    gw_lat, gw_lon = -1.25164, -78.62765
    if haversine:
        a = math.sin(math.radians(lat - gw_lat) / 2) ** 2
        a += math.cos(math.radians(gw_lat)) * math.cos(math.radians(lat)) * math.sin(math.radians(lon - gw_lon) / 2) ** 2
        horizontal = 2 * radius * math.asin(math.sqrt(min(1, max(0, a))))
    else:
        dx = math.radians(lon - gw_lon) * radius * math.cos(math.radians(-1.2417))
        dy = math.radians(lat - gw_lat) * radius
        horizontal = math.hypot(dx, dy)
    distance = max(math.sqrt(horizontal**2 + (alt - height) ** 2), 1.0)
    clutter = row["Clutter"].lower()
    exponent, loss = (2.85, 5.0) if "dense" in clutter else ((2.35, 0.0) if "park" in clutter or "periphery" in clutter else (2.65, 2.5))
    dz = height - alt
    topographic_loss = min(8 * math.log10(abs(dz)), 20.0) if dz < -10 else 0.0
    return 20.0 + 2.15 - (20 * math.log10(915.0) - 27.55) - 10 * exponent * math.log10(distance) - loss - topographic_loss


def reconstruction(rows, height, haversine):
    errors = [rf(r, height, haversine) - float(r["RSSI_Teorico_dBm"]) for r in rows]
    assert errors and max(abs(e) for e in errors) <= 0.005001
    return {"n": len(errors), "altura_efectiva_m": height,
            "distancia_horizontal": "Haversine" if haversine else "proyeccion_local",
            "error_maximo_exportacion_db": max(abs(e) for e in errors),
            "rmse_exportacion_db": math.sqrt(statistics.mean(e * e for e in errors))}


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    all_sf9 = read("Comparativa_3DMSAGA_vs_FieldTester_SF9_Consolidado.csv")
    visited = read("Puntos_Evaluados_3DMSAGA_vs_FieldTester_SF9.csv")
    sf7 = read("CoincidenciasAnalisis_US915_SF7_20dBm.csv")
    sf9_master = read("CoincidenciasAnalisis_US915_SF9_20dBm.csv")
    assert len(all_sf9) == 2154 and len(visited) == 270
    assert len({r["Node_ID"] for r in all_sf9}) == len(all_sf9)
    assert metrics(visited)["n_rssi"] == 112
    assert sum(r["Estado_Empirico"] == "Punto_Ciego_Sin_ACK" for r in visited) == 158
    assert metrics(sf7)["n_rssi"] == 49 and metrics(sf9_master)["n_rssi"] == 30
    summaries = []
    for name, rows in [("B2_SF9_global_archivado", visited),
                       ("C_SF7_Master_US915_20dBm", sf7),
                       ("SF9_Master_US915_20dBm_n30", sf9_master)]:
        summaries.append({"cohorte": name, **metrics(rows)})
    route_rows = []
    for route in ("Ruta 1", "Ruta 2", "Ruta 3", "Ruta 4"):
        rows = [r for r in visited if r["Ruta"] == route]
        n = metrics(rows)["n_rssi"]
        route_rows.append({"ruta": route, "evaluados": len(rows), "con_rssi": n,
                           "sin_rssi": len(rows) - n, "fraccion_con_rssi_pct": 100 * n / len(rows),
                           "rango_maximo_observado_m": max(float(r["Dist_GW_m"]) for r in rows if r["RSSI_Empirico_dBm"]),
                           **{k: v for k, v in metrics(rows).items() if k != "n_rssi"}})
    routed = [r for r in visited if r["Ruta"] in {"Ruta 1", "Ruta 2", "Ruta 3", "Ruta 4"}]
    n = metrics(routed)["n_rssi"]
    route_rows.append({"ruta": "Total_union_actual_4rutas", "evaluados": len(routed), "con_rssi": n,
                       "sin_rssi": len(routed) - n, "fraccion_con_rssi_pct": 100 * n / len(routed),
                       "rango_maximo_observado_m": max(float(r["Dist_GW_m"]) for r in routed if r["RSSI_Empirico_dBm"]),
                       **{k: v for k, v in metrics(routed).items() if k != "n_rssi"}})
    assert (len(routed), n, len(routed) - n) == (234, 101, 133)
    result = {
        "auditoria_ok": True,
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "alcance": "Recálculo de CSV archivados y fidelidad del predictor singleGW; no nueva campaña ni prueba externa independiente.",
        "signo_residual": "RSSI_empirico - RSSI_teorico",
        "n_malla_campo": len(all_sf9), "n_visitados_b2": len(visited),
        "n_con_rssi_b2": 112, "n_sin_rssi_b2": 158,
        "fraccion_nodos_con_rssi_b2_pct": 100 * 112 / 270,
        "no_equivale_pdr_paquetes": True,
        "cohortes": summaries,
        "rutas": route_rows,
        "reconstruccion_rf": {
            "B2_2154": reconstruction(all_sf9, 2707.0, True),
            "C_SF7_49": reconstruction(sf7, 2700.0, False),
            "SF9_Master_30": reconstruction(sf9_master, 2700.0, False),
        },
        "transcripcion_original_B1": {"n_evaluados": 200, "n_con_enlace": 83,
            "n_sin_enlace": 117, "rmse_db": 13.14, "mae_db": 9.84,
            "similitud_6db_pct": 39.8,
            "estado": "Conservada de tesis original; no se identificó el CSV exacto de esta cohorte. No reemplaza la unión actual de rutas ni el global B2."},
        "limitaciones": [
            "El procesamiento histórico conserva el RSSI máximo por nodo, no su media.",
            "B2 incluye campañas AU915/US915 y potencias 20/30 dBm; su predictor se fija a 20 dBm.",
            "La disponibilidad de RSSI se emplea como indicador de enlace en scratch_process_sf9.py; no sustituye una auditoría de contadores ACK ni fija el sentido de medición.",
            "La suite describe parámetros calibrados con la campaña; no hay partición documentada de calibración/validación reservada.",
            "Master usa altura efectiva 2700 m y B2 usa 2707 m; son variantes identificadas, no valores intercambiables.",
            "Las fracciones se refieren a nodos de las cohortes y no al área cubierta de la ciudad.",
        ],
        "fuentes_sha256": {str(p.relative_to(BASE)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(INPUT.rglob('*')) if p.is_file()},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (BASE / "Auditoria_campo_recalculada.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(BASE / "Resumen_metricas_campo_recalculadas.csv", summaries)
    write_csv(BASE / "Desglose_4rutas_recalculado.csv", route_rows)
    print(json.dumps({"auditoria_ok": True, "cohortes": summaries,
                      "total_actual_rutas": route_rows[-1],
                      "reconstruccion_rf": result["reconstruccion_rf"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
