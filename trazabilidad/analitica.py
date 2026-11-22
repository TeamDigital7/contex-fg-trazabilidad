"""Analítica del negocio: KPIs fundamentales e indicadores del SGC de Contex.

Sin Streamlit. Junta lo que ya calculan los otros módulos —pedidos (modelo) y
costo real por OT (costos)— en una serie MENSUAL y en indicadores con meta.

Las metas de calidad son las de Contex, no inventadas:
- Satisfacción del cliente (ISC): FO-EST-CONT-03, Tablero de Objetivos SGC, objetivo 1.
- Cumplimiento del plazo de entrega y conformidad del producto: CA-OPE-CONT-01.
- Tiempo de procesamiento de pedidos: indicador del informe final del ERP (meta 2026: 60 %).
- Calidad del corte: CA-OPE-CONT-01; se alimenta del FO-OPE-CONT-02 (Seguimiento de corte),
  que todavía no llega a la app: se muestra como «Por conectar», nunca con un número inventado.
Margen bruto y costo de no calidad no tienen meta en los documentos: van marcados
como metas de la app, para que el equipo las ajuste.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date

import pandas as pd

from trazabilidad.modelo import ETAPAS, Pedido, atrasado, en_riesgo

TERMINADAS = ("inspeccion", "despacho", "entregado")


@dataclass(frozen=True)
class Indicador:
    clave: str
    nombre: str
    formula: str
    fuente: str
    frecuencia: str
    bueno: float
    regular: float
    mayor_es_mejor: bool = True
    meta_propia: bool = False  # True = meta puesta por la app, no por el SGC

    def estado(self, valor: float | None) -> tuple[str, str]:
        """(texto, tono) con la banda Malo / Regular / Bueno del propio tablero de objetivos."""
        if valor is None:
            return "Por conectar", "gris"
        if self.mayor_es_mejor:
            if valor >= self.bueno:
                return "Bueno", "verde"
            return ("Regular", "ambar") if valor >= self.regular else ("Malo", "rojo")
        if valor <= self.bueno:
            return "Bueno", "verde"
        return ("Regular", "ambar") if valor <= self.regular else ("Malo", "rojo")

    @property
    def meta_texto(self) -> str:
        signo = "≥" if self.mayor_es_mejor else "≤"
        return f"{signo} {self.bueno:.0%}"


INDICADORES = (
    Indicador("isc", "Satisfacción del cliente (ISC)", "Nota promedio de las encuestas ÷ 5",
              "FO-EST-CONT-03 · objetivo 1", "Semestral", 0.85, 0.80),
    Indicador("plazo", "Cumplimiento del plazo de entrega", "Entregas a tiempo ÷ entregas",
              "CA-OPE-CONT-01", "Mensual", 0.95, 0.90),
    Indicador("conformidad", "Conformidad del producto", "Entregas sin no conformes ÷ entregas",
              "CA-OPE-CONT-01", "Mensual", 0.95, 0.90),
    Indicador("procesamiento", "Tiempo de procesamiento de pedidos", "OT terminadas ÷ OT generadas",
              "Informe final del ERP (meta 2026)", "Mensual", 0.60, 0.30),
    Indicador("margen", "Margen bruto", "(Venta − costo real) ÷ venta, sin IGV",
              "Meta de la app (ajustable)", "Mensual", 0.25, 0.15, meta_propia=True),
    Indicador("no_calidad", "Costo de no calidad", "(Merma + arreglos) ÷ costo de producción",
              "Meta de la app (ajustable)", "Mensual", 0.02, 0.04, mayor_es_mejor=False, meta_propia=True),
    Indicador("corte", "Calidad del corte", "Piezas bien cortadas ÷ piezas cortadas",
              "CA-OPE-CONT-01 · FO-OPE-CONT-02", "Mensual", 0.95, 0.90),
)
INDICADOR = {i.clave: i for i in INDICADORES}


def mes(d: date | None) -> str | None:
    return None if d is None else f"{d.year}-{d.month:02d}"


def meses_hacia_atras(hoy: date, n: int) -> list[str]:
    salida, y, m = [], hoy.year, hoy.month
    for _ in range(n):
        salida.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return salida[::-1]


@dataclass
class Analisis:
    meses: list[str]
    por_mes: pd.DataFrame
    kpis: dict
    previos: dict
    indicadores: list[dict]
    por_cliente: pd.DataFrame
    pipeline: pd.DataFrame
    materiales: pd.DataFrame


def _ratio(a: float, b: float) -> float | None:
    return (a / b) if b else None


def _mensual(pedidos: list[Pedido], meses: list[str], costo_ot: dict[str, float],
             no_calidad_mes: dict[str, float], costo_mes: dict[str, float]) -> pd.DataFrame:
    filas = []
    for m in meses:
        ent = [p for p in pedidos if p.entregado and mes(p.fecha_entregado or p.fecha_entrega) == m]
        con_precio = [p for p in ent if p.con_precios and p.codigo in costo_ot]
        ventas = sum(p.subtotal for p in con_precio)
        costo = sum(costo_ot[p.codigo] for p in con_precio)
        encuestas = [p.encuesta for p in ent if p.encuesta is not None]
        nuevos = [p for p in pedidos if mes(p.fecha_pedido) == m]
        filas.append({
            "Mes": m,
            "Pedidos nuevos": len(nuevos),
            "Entregados": len(ent),
            "Unidades entregadas": sum(p.cantidad_total for p in ent),
            "Ventas": ventas,
            "Costo": costo,
            "Margen": ventas - costo,
            "Margen %": _ratio(ventas - costo, ventas),
            "A tiempo %": _ratio(sum(1 for p in ent if (p.fecha_entregado or p.fecha_entrega) <= p.fecha_entrega), len(ent)),
            "Conformidad %": _ratio(sum(1 for p in ent if not p.no_conformes), len(ent)),
            "ISC %": (sum(encuestas) / len(encuestas) / 5) if encuestas else None,
            "No calidad %": _ratio(no_calidad_mes.get(m, 0.0), costo_mes.get(m, 0.0)),
            "Procesamiento %": _ratio(sum(1 for p in nuevos if p.etapa in TERMINADAS), len(nuevos)),
        })
    return pd.DataFrame(filas)


def _ventana(pedidos: list[Pedido], meses: list[str], costo_ot: dict[str, float],
             no_calidad_mes: dict[str, float], costo_mes: dict[str, float], hoy: date) -> dict:
    ms = set(meses)
    ent = [p for p in pedidos if p.entregado and mes(p.fecha_entregado or p.fecha_entrega) in ms]
    con_precio = [p for p in ent if p.con_precios and p.codigo in costo_ot]
    ventas = sum(p.subtotal for p in con_precio)
    costo = sum(costo_ot[p.codigo] for p in con_precio)
    encuestas = [p.encuesta for p in ent if p.encuesta is not None]
    nuevos = [p for p in pedidos if mes(p.fecha_pedido) in ms]
    activos = [p for p in pedidos if not p.entregado]
    nc = sum(v for k, v in no_calidad_mes.items() if k in ms)
    cm = sum(v for k, v in costo_mes.items() if k in ms)
    return {
        "ventas": ventas, "costo": costo, "margen": ventas - costo, "margen_pct": _ratio(ventas - costo, ventas),
        "entregados": len(ent), "unidades": sum(p.cantidad_total for p in ent),
        "ticket": _ratio(ventas, len(con_precio)),
        "costo_unitario": _ratio(costo, sum(p.cantidad_total for p in con_precio)),
        "plazo": _ratio(sum(1 for p in ent if (p.fecha_entregado or p.fecha_entrega) <= p.fecha_entrega), len(ent)),
        "conformidad": _ratio(sum(1 for p in ent if not p.no_conformes), len(ent)),
        "isc": (sum(encuestas) / len(encuestas) / 5) if encuestas else None,
        "encuestas": len(encuestas),
        "procesamiento": _ratio(sum(1 for p in nuevos if p.etapa in TERMINADAS), len(nuevos)),
        "no_calidad": _ratio(nc, cm), "no_calidad_monto": nc,
        "nuevos": len(nuevos),
        "activos": len(activos), "unidades_en_curso": sum(p.cantidad_total for p in activos),
        "en_riesgo": sum(1 for p in activos if en_riesgo(p, hoy) or atrasado(p, hoy)),
        "corte": None,  # FO-OPE-CONT-02 todavía no llega a la app
        "clientes": len({p.cliente for p in ent}),
    }


def analizar(pedidos: list[Pedido], resultado_costos, hoy: date, n_meses: int = 12,
             cliente: str | None = None) -> Analisis:
    """`resultado_costos`: costos.costear(...) de TODO el historial (o None si no hay costos)."""
    if cliente:
        pedidos = [p for p in pedidos if p.cliente == cliente]
    codigos = {p.codigo for p in pedidos}
    meses = meses_hacia_atras(hoy, n_meses)
    previos_meses = meses_hacia_atras(date(int(meses[0][:4]), int(meses[0][5:]), 1), n_meses + 1)[:-1]

    costo_ot: dict[str, float] = {}
    no_calidad_mes: dict[str, float] = {}
    costo_mes: dict[str, float] = {}
    materiales = pd.DataFrame(columns=["Material", "Gasto", "% del gasto", "% acumulado"])
    if resultado_costos is not None and len(resultado_costos.por_ot):
        po = resultado_costos.por_ot
        costo_ot = dict(zip(po["OT"], po["Costo total"]))
        mp = resultado_costos.materiales[resultado_costos.materiales["OT"].isin(codigos)].copy()
        mo = resultado_costos.mano_obra[resultado_costos.mano_obra["OT"].isin(codigos)].copy()
        te = resultado_costos.terceros[resultado_costos.terceros["OT"].isin(codigos)].copy()
        for df in (mp, mo, te):
            df["Mes"] = pd.to_datetime(df["Fecha"]).dt.strftime("%Y-%m")
        mp["merma_val"] = mp["Merma"].fillna(0) * mp["Costo unit."].fillna(0)
        for m, v in mp.groupby("Mes")["merma_val"].sum().items():
            no_calidad_mes[m] = no_calidad_mes.get(m, 0) + float(v)
        for df in (mo, te):
            for m, v in df[df["Proceso"] == "ARR"].groupby("Mes")["Costo"].sum().items():
                no_calidad_mes[m] = no_calidad_mes.get(m, 0) + float(v)
        for df in (mp, mo, te):
            for m, v in df.groupby("Mes")["Costo"].sum().items():
                costo_mes[m] = costo_mes.get(m, 0) + float(v)
        en_ventana = mp[mp["Mes"].isin(meses)]
        gasto = en_ventana.groupby("Material")["Costo"].sum().sort_values(ascending=False)
        if len(gasto):
            top = gasto.head(8)
            if len(gasto) > 8:
                top = pd.concat([top, pd.Series({"Otros materiales": gasto.iloc[8:].sum()})])
            total = float(gasto.sum())
            materiales = pd.DataFrame({"Material": top.index, "Gasto": top.values})
            materiales["% del gasto"] = materiales["Gasto"] / total
            materiales["% acumulado"] = materiales["% del gasto"].cumsum()

    por_mes = _mensual(pedidos, meses, costo_ot, no_calidad_mes, costo_mes)
    kpis = _ventana(pedidos, meses, costo_ot, no_calidad_mes, costo_mes, hoy)
    previos = _ventana(pedidos, previos_meses, costo_ot, no_calidad_mes, costo_mes, hoy)

    serie_de = {"isc": "ISC %", "plazo": "A tiempo %", "conformidad": "Conformidad %",
                "procesamiento": "Procesamiento %", "margen": "Margen %", "no_calidad": "No calidad %"}
    indicadores = []
    for ind in INDICADORES:
        valor = kpis.get("margen_pct" if ind.clave == "margen" else ind.clave)
        texto, tono = ind.estado(valor)
        serie = por_mes[serie_de[ind.clave]].tolist() if ind.clave in serie_de else []
        indicadores.append({"indicador": ind, "valor": valor, "estado": texto, "tono": tono, "serie": serie})

    # Por cliente (entregas de la ventana)
    filas = []
    ms = set(meses)
    for c in sorted({p.cliente for p in pedidos}):
        ent = [p for p in pedidos if p.cliente == c and p.entregado
               and mes(p.fecha_entregado or p.fecha_entrega) in ms]
        if not ent:
            continue
        cp = [p for p in ent if p.con_precios and p.codigo in costo_ot]
        ventas = sum(p.subtotal for p in cp)
        costo = sum(costo_ot[p.codigo] for p in cp)
        enc = [p.encuesta for p in ent if p.encuesta is not None]
        filas.append({
            "Cliente": c, "Pedidos": len(ent), "Unidades": sum(p.cantidad_total for p in ent), "Ventas": ventas,
            "Margen %": _ratio(ventas - costo, ventas),
            "A tiempo %": sum(1 for p in ent if (p.fecha_entregado or p.fecha_entrega) <= p.fecha_entrega) / len(ent),
            "ISC %": (sum(enc) / len(enc) / 5) if enc else None,
        })
    por_cliente = pd.DataFrame(filas, columns=["Cliente", "Pedidos", "Unidades", "Ventas", "Margen %",
                                               "A tiempo %", "ISC %"]).sort_values("Ventas", ascending=False)

    activos = [p for p in pedidos if not p.entregado]
    pipeline = pd.DataFrame([{
        "Etapa": e.nombre,
        "Pedidos": sum(1 for p in activos if p.etapa == e.clave),
        "Unidades": sum(p.cantidad_total for p in activos if p.etapa == e.clave),
        "En riesgo": sum(1 for p in activos if p.etapa == e.clave and (en_riesgo(p, hoy) or atrasado(p, hoy))),
    } for e in ETAPAS if e.clave != "entregado"])

    return Analisis(meses, por_mes, kpis, previos, indicadores, por_cliente, pipeline, materiales)


def comparable(a: "Analisis") -> bool:
    """¿El periodo anterior tiene datos suficientes para compararse?

    Contra un periodo casi vacío cualquier variación sale gigante (+2.000 %) y no
    dice nada. Se compara solo si el anterior tuvo al menos 60 % de las entregas.
    """
    return a.previos["entregados"] >= max(3, 0.6 * a.kpis["entregados"])


def variacion(actual: float | None, previo: float | None) -> float | None:
    if actual is None or not previo:
        return None
    return (actual - previo) / abs(previo)


# --- Reporte descargable --------------------------------------------------------

def excel_kpis(a: Analisis, alcance: str) -> bytes:
    import xlsxwriter

    salida = io.BytesIO()
    libro = xlsxwriter.Workbook(salida, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    t = libro.add_format({"bold": True, "font_size": 15, "font_color": "#12386B"})
    sub = libro.add_format({"font_color": "#667085"})
    cab = libro.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#12386B", "text_wrap": True,
                            "valign": "vcenter"})
    sol = libro.add_format({"num_format": '"S/" #,##0'})
    pct = libro.add_format({"num_format": "0.0%"})
    tonos = {"verde": "#E3F4E8", "ambar": "#FEF3D6", "rojo": "#FDE8E7", "gris": "#EEF1F5"}

    h = libro.add_worksheet("Indicadores")
    h.set_column(0, 0, 38)
    h.set_column(1, 6, 18)
    h.write(0, 0, "Reporte de KPIs · Contex FYG", t)
    h.write(1, 0, f"{alcance} · {a.meses[0]} a {a.meses[-1]}", sub)
    h.write_row(3, 0, ["Indicador", "Valor", "Meta", "Estado", "Fórmula", "Fuente", "Frecuencia"], cab)
    for i, d in enumerate(a.indicadores, start=4):
        ind = d["indicador"]
        h.write(i, 0, ind.nombre)
        if d["valor"] is None:
            h.write(i, 1, "Por conectar")
        else:
            h.write_number(i, 1, d["valor"], pct)
        h.write(i, 2, ind.meta_texto)
        h.write(i, 3, d["estado"], libro.add_format({"bg_color": tonos[d["tono"]], "bold": True}))
        h.write(i, 4, ind.formula)
        h.write(i, 5, ind.fuente)
        h.write(i, 6, ind.frecuencia)
    k = a.kpis
    fila = 6 + len(a.indicadores)
    h.write(fila, 0, "Negocio", libro.add_format({"bold": True, "font_color": "#12386B"}))
    for j, (nombre, valor, fmt) in enumerate([
        ("Ventas (sin IGV)", k["ventas"], sol), ("Costo real de lo entregado", k["costo"], sol),
        ("Margen bruto", k["margen"], sol), ("Pedidos entregados", k["entregados"], None),
        ("Unidades entregadas", k["unidades"], None), ("Ticket promedio", k["ticket"], sol),
        ("Costo unitario promedio", k["costo_unitario"], sol), ("Pedidos en curso", k["activos"], None),
        ("En riesgo o atrasados", k["en_riesgo"], None)], start=fila + 1):
        h.write(j, 0, nombre)
        if valor is None:
            h.write(j, 1, "-")
        elif fmt:
            h.write_number(j, 1, valor, fmt)
        else:
            h.write_number(j, 1, valor)

    def hoja(nombre, df, formatos):
        w = libro.add_worksheet(nombre)
        w.write_row(0, 0, list(df.columns), cab)
        for j, c in enumerate(df.columns):
            w.set_column(j, j, max(12, min(40, len(str(c)) + 6)))
        for i, r in enumerate(df.itertuples(index=False), start=1):
            for j, (c, v) in enumerate(zip(df.columns, r)):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    continue
                if isinstance(v, (int, float)) and c in formatos:
                    w.write_number(i, j, float(v), formatos[c])
                else:
                    w.write(i, j, v)
        w.freeze_panes(1, 1)

    porc = {c: pct for c in ("Margen %", "A tiempo %", "Conformidad %", "ISC %", "No calidad %", "Procesamiento %",
                             "% del gasto", "% acumulado")}
    plata = {c: sol for c in ("Ventas", "Costo", "Margen", "Gasto")}
    hoja("Por mes", a.por_mes, {**porc, **plata})
    hoja("Por cliente", a.por_cliente, {**porc, **plata})
    hoja("Pedidos en curso", a.pipeline, {})
    hoja("Pareto de materiales", a.materiales, {**porc, **plata})
    libro.close()
    return salida.getvalue()


def pdf_kpis(a: Analisis, alcance: str, hoy: date, demo: bool = False) -> bytes:
    from trazabilidad.reportes import TONOS, Documento, fecha_corta, soles, t as lat

    k = a.kpis
    doc = Documento("REPORTE DE KPIs", f"{alcance} · {a.meses[0]} a {a.meses[-1]} · al {fecha_corta(hoy)}", "L", demo)
    doc.add_page()
    tarjetas = [("Ventas (sin IGV)", soles(k["ventas"]), f"{k['entregados']} pedidos entregados"),
                ("Margen bruto", "-" if k["margen_pct"] is None else f"{k['margen_pct']:.1%}", soles(k["margen"])),
                ("Entregas a tiempo", "-" if k["plazo"] is None else f"{k['plazo']:.0%}", "meta ≥ 95 %"),
                ("Satisfacción (ISC)", "-" if k["isc"] is None else f"{k['isc']:.0%}", f"{k['encuestas']} encuestas"),
                ("Costo unitario", soles(k["costo_unitario"]), f"{k['unidades']:,} prendas"),
                ("En curso", str(k["activos"]), f"{k['en_riesgo']} en riesgo")]
    ancho = (doc.w - 28 - 5 * 4) / 6
    y = doc.get_y()
    for i, (x1, x2, x3) in enumerate(tarjetas):
        doc.tarjeta_dato(14 + i * (ancho + 4), y, ancho, x1, x2, x3)
    doc.set_y(y + 25)

    doc.seccion("Indicadores del sistema de gestión de calidad")
    # tabla con semáforo: el estado va en texto Y color (nunca solo color)
    anchos = (70, 24, 22, 28, 70, 55)
    doc.set_font("Helvetica", "B", 8.5)
    doc.set_fill_color(18, 56, 107)
    doc.set_text_color(255, 255, 255)
    for w_, c in zip(anchos, ("Indicador", "Valor", "Meta", "Estado", "Fórmula", "Fuente")):
        doc.cell(w_, 7, lat(c), fill=True)
    doc.ln()
    doc.set_font("Helvetica", "", 8.5)
    for d in a.indicadores:
        ind = d["indicador"]
        fondo, color = TONOS[d["tono"]]
        doc.set_text_color(20, 33, 61)
        doc.cell(anchos[0], 7, lat(ind.nombre))
        doc.cell(anchos[1], 7, "-" if d["valor"] is None else f"{d['valor']:.1%}", align="R")
        doc.cell(anchos[2], 7, lat(ind.meta_texto), align="C")
        doc.set_fill_color(*fondo)
        doc.set_text_color(*color)
        doc.set_font("Helvetica", "B", 8.5)
        doc.cell(anchos[3], 7, lat(d["estado"]), align="C", fill=True)
        doc.set_font("Helvetica", "", 8)
        doc.set_text_color(102, 112, 133)
        doc.cell(anchos[4], 7, lat(ind.formula))
        doc.cell(anchos[5], 7, lat(ind.fuente), new_x="LMARGIN", new_y="NEXT")
        doc.set_font("Helvetica", "", 8.5)
    doc.set_text_color(20, 33, 61)

    doc.add_page()
    doc.seccion("Evolución mensual")
    pm = a.por_mes
    doc.tabla(("Mes", "Nuevos", "Entregados", "Ventas", "Costo", "Margen", "A tiempo", "Conformidad", "ISC"),
              [(r["Mes"], str(r["Pedidos nuevos"]), str(r["Entregados"]), soles(r["Ventas"]), soles(r["Costo"]),
                "-" if r["Margen %"] is None or pd.isna(r["Margen %"]) else f"{r['Margen %']:.1%}",
                "-" if r["A tiempo %"] is None or pd.isna(r["A tiempo %"]) else f"{r['A tiempo %']:.0%}",
                "-" if r["Conformidad %"] is None or pd.isna(r["Conformidad %"]) else f"{r['Conformidad %']:.0%}",
                "-" if r["ISC %"] is None or pd.isna(r["ISC %"]) else f"{r['ISC %']:.0%}")
               for r in pm.to_dict("records")],
              (24, 20, 24, 34, 34, 24, 24, 28, 22), ("LEFT",) + ("RIGHT",) * 8)
    if len(a.por_cliente):
        doc.seccion("Por cliente")
        doc.tabla(("Cliente", "Pedidos", "Unidades", "Ventas", "Margen", "A tiempo", "ISC"),
                  [(r["Cliente"], str(r["Pedidos"]), f"{r['Unidades']:,}", soles(r["Ventas"]),
                    "-" if pd.isna(r["Margen %"]) else f"{r['Margen %']:.1%}", f"{r['A tiempo %']:.0%}",
                    "-" if r["ISC %"] is None or pd.isna(r["ISC %"]) else f"{r['ISC %']:.0%}")
                   for r in a.por_cliente.to_dict("records")],
                  (90, 22, 26, 36, 26, 26, 22), ("LEFT",) + ("RIGHT",) * 6)
    return bytes(doc.output())
