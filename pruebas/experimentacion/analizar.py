# Resume las corridas de resultados/ en resultados/resumen.json.
# Las cifras por etiqueta salen del statistics.json del reporte HTML de JMeter
# (las mismas columnas del reporte); los cortes por tiempo salen del .jtl.
#
# Uso: python analizar.py
import csv
import json
import os
import statistics
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")


def leer_jtl(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        r["ts"] = int(r["timeStamp"])
        r["ms"] = int(r["elapsed"])
        r["ok"] = r["success"] == "true"
        r["hilos"] = int(r["allThreads"] or 0)
    return filas


def p95(valores):
    if not valores:
        return None
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def resumen_ventana(filas):
    if not filas:
        return {"muestras": 0}
    t0 = min(r["ts"] for r in filas)
    t1 = max(r["ts"] + r["ms"] for r in filas)
    seg = max((t1 - t0) / 1000, 0.001)
    tiempos = [r["ms"] for r in filas]
    err = sum(1 for r in filas if not r["ok"])
    return {
        "muestras": len(filas),
        "media_ms": round(statistics.mean(tiempos), 1),
        "p95_ms": p95(tiempos),
        "max_ms": max(tiempos),
        "error_pct": round(100 * err / len(filas), 2),
        "throughput": round(len(filas) / seg, 1),
    }


def cortes(filas, inicio, ventanas):
    """ventanas: lista de (nombre, desde_s, hasta_s) relativas al inicio de la prueba."""
    out = {}
    for nombre, a, b in ventanas:
        sel = [r for r in filas if inicio + a * 1000 <= r["ts"] < inicio + b * 1000]
        res = resumen_ventana(sel)
        res["segundos"] = b - a
        if sel:
            ok = [r for r in sel if r["ok"]]
            res["throughput"] = round(len(sel) / (b - a), 1)
            res["exitosas_por_s"] = round(len(ok) / (b - a), 1)
            res["media_ok_ms"] = round(statistics.mean(r["ms"] for r in ok), 1) if ok else None
            res["hilos_activos_max"] = max(r["hilos"] for r in sel)
        out[nombre] = res
    return out


def errores(filas):
    c = Counter()
    for r in filas:
        if not r["ok"]:
            msg = r["responseMessage"] or r["failureMessage"]
            c[f'{r["label"]} | {r["responseCode"]} | {msg[:90]}'] += 1
    return dict(c.most_common(8))


def perfmon(ruta, inicio=None, fin=None):
    if not os.path.exists(ruta):
        return None
    series = defaultdict(list)
    with open(ruta, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ts = int(r["timeStamp"])
            if inicio and (ts < inicio or ts > fin):
                continue
            series[r["label"]].append((ts, int(r["elapsed"]) / 1000.0))
    out = {}
    for etiqueta, vals in series.items():
        v = [x for _, x in vals]
        clave = etiqueta.replace("localhost ", "")
        if "resident" in clave:
            v = [x / 1024 / 1024 for x in v]  # bytes -> MB
            clave = "Memoria API (MB)"
        elif clave.startswith("CPU pid"):
            clave = "CPU API (%)"
        elif clave == "CPU":
            clave = "CPU equipo (%)"
        elif clave == "Memory":
            clave = "Memoria equipo (%)"
        out[clave] = {"media": round(statistics.mean(v), 1), "max": round(max(v), 1),
                      "min": round(min(v), 1), "inicio": round(v[0], 1), "final": round(v[-1], 1),
                      "muestras": len(v)}
    return out


def main():
    resumen = {}
    for corrida in sorted(os.listdir(RES)):
        d = os.path.join(RES, corrida)
        jtl = os.path.join(d, "resultados.jtl")
        stats = os.path.join(d, "reporte", "statistics.json")
        if not (os.path.isdir(d) and os.path.exists(jtl) and os.path.exists(stats)):
            continue
        with open(stats, encoding="utf-8") as f:
            st = json.load(f)
        filas = leer_jtl(jtl)
        inicio = min(r["ts"] for r in filas)
        fin = max(r["ts"] + r["ms"] for r in filas)
        info = {
            "duracion_s": round((fin - inicio) / 1000, 1),
            "hilos_activos_max": max(r["hilos"] for r in filas),
            "reporte": {k: {"muestras": v["sampleCount"], "errores": v["errorCount"],
                            "error_pct": round(v["errorPct"], 2), "media_ms": round(v["meanResTime"], 2),
                            "mediana_ms": v["medianResTime"], "p95_ms": v["pct2ResTime"],
                            "max_ms": v["maxResTime"], "throughput": round(v["throughput"], 2)}
                        for k, v in st.items()},
            "errores": errores(filas),
        }
        if corrida.startswith(("p01", "p04", "p10")):
            # Linea de tiempo cada 10 s: muestras, exitosas por segundo, errores y media de las exitosas
            linea = []
            for s in range(0, int((fin - inicio) / 1000) + 1, 10):
                sel = [r for r in filas if inicio + s * 1000 <= r["ts"] < inicio + (s + 10) * 1000]
                if not sel:
                    continue
                ok = [r for r in sel if r["ok"]]
                linea.append({"desde_s": s, "muestras": len(sel), "exitosas_por_s": round(len(ok) / 10, 1),
                              "errores": len(sel) - len(ok),
                              "media_ok_ms": round(statistics.mean(r["ms"] for r in ok), 1) if ok else None,
                              "hilos": max(r["hilos"] for r in sel)})
            info["linea_10s"] = linea
            fallos_puerto = [r["ts"] for r in filas if "BindException" in (r["responseMessage"] + r["responseCode"])]
            if fallos_puerto:
                primero = min(fallos_puerto)
                info["primer_bind_s"] = round((primero - inicio) / 1000, 1)
                previas = [r for r in filas if r["ts"] < primero]
                info["conexiones_antes_del_primer_bind"] = len(previas)
                info["antes_del_primer_bind"] = resumen_ventana(previas)
                info["despues_del_primer_bind"] = resumen_ventana([r for r in filas if r["ts"] >= primero])
        if corrida.startswith("p02"):
            info["cortes"] = cortes(filas, inicio, [("primeros_10s", 0, 10), ("10s_a_70s", 10, 70),
                                                    ("ultimos_50s", 70, 120)])
            por_seg = defaultdict(list)
            for r in filas:
                por_seg[(r["ts"] - inicio) // 1000].append(r["ms"])
            info["por_segundo_0_15"] = {int(s): {"n": len(v), "media": round(statistics.mean(v), 1), "max": max(v)}
                                        for s, v in sorted(por_seg.items()) if s < 15}
        if corrida.startswith("p04"):
            fin250 = min(180, int(info.get("primer_bind_s", 180)))
            info["cortes"] = cortes(filas, inicio, [("50 usuarios", 15, 60), ("100 usuarios", 75, 120),
                                                    ("250 usuarios", 135, fin250),
                                                    ("250 usuarios, desde el error de puertos", fin250, 180),
                                                    ("500 usuarios", 195, 240)])
        if corrida.startswith("p05"):
            minutos = int(round((fin - inicio) / 60000))
            info["cortes"] = cortes(filas, inicio, [(f"minuto {m + 1}", m * 60, (m + 1) * 60)
                                                    for m in range(max(minutos, 1))])
        if corrida.startswith(("p07", "p08")):
            sel = [r for r in filas if r["label"] == "SeleccionTarifaYCantidad"]
            ok = [r for r in sel if r["ok"]]
            ids = [r.get("num_reserva") for r in ok]
            info["seleccion"] = {
                "enviadas": len(sel), "exitosas": len(ok),
                "reservas_unicas": len(set(ids)), "reservas_repetidas": len(ids) - len(set(ids)),
                "ventana_envio_ms": max(r["ts"] for r in sel) - min(r["ts"] for r in sel),
                "max_ms_exitosas": max((r["ms"] for r in ok), default=None),
            }
        if corrida.startswith("p10") or corrida.startswith("p05"):
            info["perfmon"] = perfmon(os.path.join(d, "perfmon.csv"), inicio, fin)
            if corrida.startswith("p10"):
                info["cortes"] = cortes(filas, inicio, [("subida 0-60s", 0, 60), ("carga plena 60-180s", 60, 180)])
                info["perfmon_carga_plena"] = perfmon(os.path.join(d, "perfmon.csv"), inicio + 60000, fin)
                if "primer_bind_s" in info:
                    corte = inicio + int(info["primer_bind_s"] * 1000)
                    info["perfmon_antes_bind"] = perfmon(os.path.join(d, "perfmon.csv"), inicio, corte)
                    info["perfmon_despues_bind"] = perfmon(os.path.join(d, "perfmon.csv"), corte, fin)
        resumen[corrida] = info

    with open(os.path.join(RES, "resumen.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
