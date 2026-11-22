"""Módulo de costos: costo real de cada orden de trabajo (OT) y cierre mensual.

Sin Streamlit. Sigue el modelo del ERP de Contex (liquidación de órdenes de
proceso) y le agrega lo que el reporte «Costos de Orden de Trabajo» no tiene:

    costo de la OT = materia prima consumida (+ merma)      <- liquidación / kardex
                   + mano de obra directa (horas x tarifa)  <- liquidación
                   + servicios de terceros                  <- orden de proceso
                   + costos indirectos asignados (CIF)      <- centros de costo + regla

**Los CIF se reparten con una regla explícita**, no a ojo:
- los de un centro PRODUCTIVO (Corte, Bordado, Estampado, Confección) solo van a
  las OT que pasaron por ese proceso en el periodo, según la base elegida;
- los del centro de APOYO (planta general: alquiler, energía, jefatura...) van a
  todas las OT del periodo, con la misma base.
La base puede ser horas de mano de obra (por defecto: la costura es la que ocupa
la planta), unidades producidas o costo de materia prima. Si un centro tiene
gasto y en el periodo no hubo ninguna OT que lo use, ese monto queda **sin
asignar** y se reporta: esconderlo inflaría el costo de las demás.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from trazabilidad.modelo import Pedido

# Procesos de Contex (procedimientos PR-OPE-CONT-02/03): el corte se hace en planta; bordado,
# estampado, confección y lavado suelen ir a talleres externos por orden de servicio
# (FO-LOG-CONT-03/04/05/12); arreglos y limpieza vuelven a la planta.
PROCESOS = {"COR": "Corte", "BOR": "Bordado", "EST": "Estampado", "CNF": "Confección",
            "LAV": "Lavado", "ARR": "Taller de arreglos", "ACA": "Limpieza y acabado"}
REPROCESO = "ARR"  # lo que se hace en arreglos es costo de no calidad
CENTRO_APOYO = "PLA"
CENTROS = {**PROCESOS, CENTRO_APOYO: "Planta general (apoyo)"}
BASES = {
    "horas": "Horas de mano de obra",
    "unidades": "Unidades producidas",
    "mp": "Costo de materia prima",
}
ELEMENTOS = ("Materia prima", "Mano de obra", "Terceros", "Indirectos (CIF)")
MARGEN_MINIMO = 0.15  # por debajo, la OT se marca para revisar

COLUMNAS = {
    "materiales": ["codigo_pedido", "fecha", "proceso", "codigo", "descripcion", "um",
                   "cant_requerida", "cant_consumida", "cant_merma", "costo_unitario"],
    "mano_obra": ["codigo_pedido", "fecha", "proceso", "personal", "horas", "tarifa_hora"],
    "terceros": ["codigo_pedido", "fecha", "proceso", "proveedor", "cantidad", "costo_unitario"],
    "cif": ["periodo", "centro", "concepto", "monto"],
}


class ErrorDeCostos(Exception):
    pass


@dataclass
class TablasCosto:
    materiales: pd.DataFrame
    mano_obra: pd.DataFrame
    terceros: pd.DataFrame
    cif: pd.DataFrame
    tarifas: dict[str, float] = field(default_factory=dict)  # tarifa hora por proceso (maestro)


@dataclass
class Resultado:
    periodo: str
    base: str
    por_ot: pd.DataFrame
    por_proceso: pd.DataFrame
    asignacion: pd.DataFrame
    desvios: pd.DataFrame
    materiales: pd.DataFrame
    mano_obra: pd.DataFrame
    terceros: pd.DataFrame
    kpis: dict


# --- Normalización -----------------------------------------------------------------

def _preparar(df: pd.DataFrame, tabla: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    obligatorias = [c for c in COLUMNAS[tabla] if c not in ("um", "descripcion", "codigo", "personal",
                                                          "proveedor", "tarifa_hora", "cant_requerida",
                                                          "cant_merma", "concepto")]
    faltan = [c for c in obligatorias if c not in df.columns]
    if faltan:
        raise ErrorDeCostos(f"A la tabla de costos '{tabla}' le faltan columnas: {', '.join(faltan)}")
    for c in COLUMNAS[tabla]:
        if c not in df.columns:
            df[c] = None
    numericas = {"cant_requerida", "cant_consumida", "cant_merma", "costo_unitario", "horas",
                 "tarifa_hora", "cantidad", "monto"}
    for c in numericas & set(df.columns):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["periodo"] = df["fecha"].dt.strftime("%Y-%m")
    if "proceso" in df.columns:
        df["proceso"] = df["proceso"].astype(str).str.strip().str.upper().str[:3]
    if "centro" in df.columns:
        df["centro"] = df["centro"].astype(str).str.strip().str.upper().str[:3]
        df["periodo"] = df["periodo"].astype(str).str[:7]
    if "codigo_pedido" in df.columns:
        df["codigo_pedido"] = df["codigo_pedido"].astype(str).str.strip()
    return df


def periodos(tablas: TablasCosto) -> list[str]:
    vistos = set()
    for df, t in ((tablas.materiales, "materiales"), (tablas.mano_obra, "mano_obra"),
                  (tablas.terceros, "terceros")):
        if len(df):
            vistos |= set(_preparar(df, t)["periodo"].dropna())
    vistos |= set(_preparar(tablas.cif, "cif")["periodo"].dropna()) if len(tablas.cif) else set()
    return sorted(vistos, reverse=True)


# --- El costeo ---------------------------------------------------------------------

def costear(pedidos: list[Pedido], tablas: TablasCosto, periodo: str | None = None,
            base: str = "horas", hoy: date | None = None) -> Resultado:
    """Costo por OT. `periodo` = "2026-11" o None (todo el historial, CIF de todos los meses)."""
    if base not in BASES:
        raise ErrorDeCostos(f"Base de asignación '{base}' no válida.")
    mp = _preparar(tablas.materiales, "materiales")
    mo = _preparar(tablas.mano_obra, "mano_obra")
    te = _preparar(tablas.terceros, "terceros")
    cif = _preparar(tablas.cif, "cif")
    if periodo:
        mp, mo, te, cif = (d[d["periodo"] == periodo] for d in (mp, mo, te, cif))

    mp = mp.assign(cant_merma=mp["cant_merma"].fillna(0), cant_requerida=mp["cant_requerida"])
    mp["costo_consumo"] = mp["cant_consumida"].fillna(0) * mp["costo_unitario"].fillna(0)
    mp["costo_merma"] = mp["cant_merma"] * mp["costo_unitario"].fillna(0)
    mp["costo"] = mp["costo_consumo"] + mp["costo_merma"]
    tarifa_maestro = mo["proceso"].map(lambda p: tablas.tarifas.get(p))
    mo["tarifa_hora"] = mo["tarifa_hora"].fillna(tarifa_maestro).fillna(0)
    mo["costo"] = mo["horas"].fillna(0) * mo["tarifa_hora"]
    te["costo"] = te["cantidad"].fillna(0) * te["costo_unitario"].fillna(0)

    info = {p.codigo: p for p in pedidos}
    codigos = sorted(set(mp["codigo_pedido"]) | set(mo["codigo_pedido"]) | set(te["codigo_pedido"]))
    codigos = [c for c in codigos if c in info]

    # Base de asignación por OT y proceso
    if base == "horas":
        base_df = mo.groupby(["codigo_pedido", "proceso"])["horas"].sum()
    elif base == "mp":
        base_df = mp.groupby(["codigo_pedido", "proceso"])["costo"].sum()
    else:  # unidades: las de la OT, una vez por cada proceso en el que tuvo actividad
        actividad = pd.concat([mp[["codigo_pedido", "proceso"]], mo[["codigo_pedido", "proceso"]],
                               te[["codigo_pedido", "proceso"]]]).drop_duplicates()
        actividad["valor"] = actividad["codigo_pedido"].map(lambda c: info[c].cantidad_total if c in info else 0)
        base_df = actividad.groupby(["codigo_pedido", "proceso"])["valor"].sum()
    base_df = base_df[base_df.index.get_level_values(0).isin(codigos)]
    base_df = base_df[base_df > 0]

    filas_asig = []
    cif_por_ot: dict[str, float] = {c: 0.0 for c in codigos}
    sin_asignar = 0.0
    for (centro, concepto), monto in cif.groupby(["centro", "concepto"], dropna=False)["monto"].sum().items():
        if not monto:
            continue
        if centro == CENTRO_APOYO:
            reparto = base_df.groupby(level=0).sum()
        else:
            reparto = base_df[base_df.index.get_level_values(1) == centro].groupby(level=0).sum()
        total_base = float(reparto.sum())
        if total_base <= 0:
            sin_asignar += float(monto)
            filas_asig.append({"Centro": CENTROS.get(centro, centro), "Concepto": concepto, "Monto": monto,
                               "OT": "— sin asignar —", "Base": 0.0, "% de la base": 0.0, "Asignado": 0.0})
            continue
        for codigo, valor in reparto.items():
            asignado = float(monto) * float(valor) / total_base
            cif_por_ot[codigo] += asignado
            filas_asig.append({"Centro": CENTROS.get(centro, centro), "Concepto": concepto, "Monto": float(monto),
                               "OT": codigo, "Base": float(valor), "% de la base": float(valor) / total_base,
                               "Asignado": asignado})

    filas = []
    for c in codigos:
        p = info[c]
        m, o, t = mp[mp["codigo_pedido"] == c], mo[mo["codigo_pedido"] == c], te[te["codigo_pedido"] == c]
        costo_mp, costo_mo, costo_te = float(m["costo"].sum()), float(o["costo"].sum()), float(t["costo"].sum())
        costo_cif = cif_por_ot.get(c, 0.0)
        total = costo_mp + costo_mo + costo_te + costo_cif
        venta = p.subtotal if p.con_precios else None
        # El margen compara la venta con el costo de TODA la OT: solo sin filtro de periodo y solo si la
        # OT ya salió de producción. Una OT a medio confeccionar tendría un margen alto y FALSO.
        terminada = p.etapa in ("inspeccion", "despacho", "entregado")
        margen = (venta - total) if (venta is not None and periodo is None and terminada) else None
        filas.append({
            "OT": c, "Cliente": p.cliente, "Producto": p.productos, "Unidades": p.cantidad_total,
            "Etapa": p.etapa, "Costo": "Final" if terminada else "En proceso", "Materia prima": costo_mp, "Merma": float(m["costo_merma"].sum()),
            "Mano de obra": costo_mo, "Terceros": costo_te, "Indirectos (CIF)": costo_cif,
            "Costo total": total, "Costo unitario": total / p.cantidad_total if p.cantidad_total else None,
            "Horas MO": float(o["horas"].sum()), "Venta (sin IGV)": venta, "Margen": margen,
            "Margen %": (margen / venta) if (margen is not None and venta) else None,
        })
    por_ot = pd.DataFrame(filas, columns=["OT", "Cliente", "Producto", "Unidades", "Etapa", "Costo", "Materia prima",
                                          "Merma", "Mano de obra", "Terceros", "Indirectos (CIF)", "Costo total",
                                          "Costo unitario", "Horas MO", "Venta (sin IGV)", "Margen", "Margen %"])

    # Por proceso / centro de costo
    asig_df = pd.DataFrame(filas_asig, columns=["Centro", "Concepto", "Monto", "OT", "Base", "% de la base", "Asignado"])
    procesos = []
    for clave, nombre in CENTROS.items():
        procesos.append({
            "Centro": nombre,
            "Materia prima": float(mp.loc[mp["proceso"] == clave, "costo"].sum()),
            "Mano de obra": float(mo.loc[mo["proceso"] == clave, "costo"].sum()),
            "Terceros": float(te.loc[te["proceso"] == clave, "costo"].sum()),
            "Indirectos (CIF)": float(cif.loc[cif["centro"] == clave, "monto"].sum()),
        })
    por_proceso = pd.DataFrame(procesos)
    por_proceso["Total"] = por_proceso[list(ELEMENTOS)].sum(axis=1)
    por_proceso = por_proceso[por_proceso["Total"] > 0].reset_index(drop=True)

    # Desvíos de consumo: lo que se usó (consumo + merma) contra lo que pedía la ficha técnica
    d = mp[mp["cant_requerida"].fillna(0) > 0].copy()
    d["usado"] = d["cant_consumida"].fillna(0) + d["cant_merma"]
    agg = d.groupby(["codigo_pedido", "codigo", "descripcion", "um"], dropna=False).agg(
        requerida=("cant_requerida", "sum"), usado=("usado", "sum"), merma=("cant_merma", "sum"),
        costo_unitario=("costo_unitario", "mean")).reset_index()
    agg["desvio"] = (agg["usado"] - agg["requerida"]) / agg["requerida"]
    agg["valor_desvio"] = (agg["usado"] - agg["requerida"]) * agg["costo_unitario"]
    desvios = agg.rename(columns={"codigo_pedido": "OT", "codigo": "Código", "descripcion": "Material", "um": "UM",
                                  "requerida": "Requerida", "usado": "Usada", "merma": "Merma",
                                  "costo_unitario": "Costo unit.", "desvio": "Desvío %",
                                  "valor_desvio": "Valor del desvío"}).sort_values("Valor del desvío", ascending=False)

    total = float(por_ot["Costo total"].sum())
    unidades = float(por_ot["Unidades"].sum()) if len(por_ot) else 0
    con_margen = por_ot.dropna(subset=["Margen"])
    venta_total = float(con_margen["Venta (sin IGV)"].sum()) if len(con_margen) else 0
    consumo_mp = float(mp["costo_consumo"].sum())
    kpis = {
        "ots": len(por_ot),
        "costo_total": total,
        "unidades": unidades,
        "costo_unitario": total / unidades if unidades else None,
        "elementos": {e: float(por_ot[e].sum()) for e in ELEMENTOS},
        "cif_total": float(cif["monto"].sum()),
        "cif_sin_asignar": sin_asignar,
        "merma": float(mp["costo_merma"].sum()),
        "merma_pct": float(mp["costo_merma"].sum()) / consumo_mp if consumo_mp else None,
        "margen_pct": (float(con_margen["Margen"].sum()) / venta_total) if venta_total else None,
        "ots_margen_bajo": int((con_margen["Margen %"] < MARGEN_MINIMO).sum()) if len(con_margen) else 0,
        "horas": float(mo["horas"].sum()),
        # Costo de no calidad: merma + todo lo gastado en el taller de arreglos (reprocesos)
        "no_calidad": float(mp["costo_merma"].sum()) + float(mo.loc[mo["proceso"] == REPROCESO, "costo"].sum())
                      + float(te.loc[te["proceso"] == REPROCESO, "costo"].sum()),
        "terceros_pct": (float(por_ot["Terceros"].sum()) / total) if total else None,
    }
    columnas_mp = mp.rename(columns={"codigo_pedido": "OT", "fecha": "Fecha", "proceso": "Proceso", "codigo": "Código",
                                     "descripcion": "Material", "um": "UM", "cant_requerida": "Requerida",
                                     "cant_consumida": "Consumida", "cant_merma": "Merma",
                                     "costo_unitario": "Costo unit.", "costo": "Costo"})
    columnas_mo = mo.rename(columns={"codigo_pedido": "OT", "fecha": "Fecha", "proceso": "Proceso",
                                     "personal": "Personal", "horas": "Horas", "tarifa_hora": "Tarifa/h",
                                     "costo": "Costo"})
    columnas_te = te.rename(columns={"codigo_pedido": "OT", "fecha": "Fecha", "proceso": "Proceso",
                                     "proveedor": "Proveedor", "cantidad": "Cantidad",
                                     "costo_unitario": "Costo unit.", "costo": "Costo"})
    return Resultado(
        periodo=periodo or "Todo", base=base, por_ot=por_ot, por_proceso=por_proceso, asignacion=asig_df,
        desvios=desvios,
        materiales=columnas_mp[["OT", "Fecha", "Proceso", "Código", "Material", "UM", "Requerida", "Consumida",
                                "Merma", "Costo unit.", "Costo"]],
        mano_obra=columnas_mo[["OT", "Fecha", "Proceso", "Personal", "Horas", "Tarifa/h", "Costo"]],
        terceros=columnas_te[["OT", "Fecha", "Proceso", "Proveedor", "Cantidad", "Costo unit.", "Costo"]],
        kpis=kpis,
    )


def detalle_ot(res: Resultado, codigo: str) -> dict[str, pd.DataFrame]:
    """Las piezas del costo de una OT, como el reporte del ERP pero con CIF y margen."""
    return {
        "materiales": res.materiales[res.materiales["OT"] == codigo],
        "mano_obra": res.mano_obra[res.mano_obra["OT"] == codigo],
        "terceros": res.terceros[res.terceros["OT"] == codigo],
        "cif": res.asignacion[res.asignacion["OT"] == codigo],
        "desvios": res.desvios[res.desvios["OT"] == codigo],
    }


# --- Exportación del cierre -----------------------------------------------------------

def excel_cierre(res: Resultado, empresa: str = "Contex FYG", cerrado: str = "") -> bytes:
    import xlsxwriter

    salida = io.BytesIO()
    libro = xlsxwriter.Workbook(salida, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    titulo = libro.add_format({"bold": True, "font_size": 15, "font_color": "#12386B"})
    sub = libro.add_format({"font_color": "#667085"})
    cab = libro.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#12386B", "text_wrap": True,
                            "valign": "vcenter"})
    sol = libro.add_format({"num_format": '"S/" #,##0.00'})
    pct = libro.add_format({"num_format": "0.0%"})
    num = libro.add_format({"num_format": "#,##0.00"})
    fec = libro.add_format({"num_format": "dd/mm/yyyy"})

    r = libro.add_worksheet("Resumen")
    r.set_column(0, 0, 34)
    r.set_column(1, 1, 18)
    r.write(0, 0, f"Cierre de costos · {res.periodo}", titulo)
    r.write(1, 0, f"{empresa} · base de asignación de CIF: {BASES[res.base]}" + (f" · {cerrado}" if cerrado else ""), sub)
    k = res.kpis
    filas = [("Órdenes de trabajo costeadas", k["ots"], None), ("Unidades", k["unidades"], num),
             ("Costo total de producción", k["costo_total"], sol), ("Costo unitario promedio", k["costo_unitario"], sol)]
    filas += [(f"  {e}", v, sol) for e, v in k["elementos"].items()]
    filas += [("CIF del periodo", k["cif_total"], sol), ("CIF sin asignar", k["cif_sin_asignar"], sol),
              ("Merma valorizada", k["merma"], sol), ("Merma / consumo de MP", k["merma_pct"], pct),
              ("Costo de no calidad (merma + arreglos)", k["no_calidad"], sol),
              ("Margen bruto (OT con precio)", k["margen_pct"], pct)]
    for i, (a, v, f) in enumerate(filas, start=3):
        r.write(i, 0, a)
        if v is None:
            r.write_blank(i, 1, None)
        elif f is None:
            r.write(i, 1, v)
        else:
            r.write_number(i, 1, float(v), f)

    def hoja(nombre, df, formatos):
        h = libro.add_worksheet(nombre)
        h.write_row(0, 0, list(df.columns), cab)
        for j, col in enumerate(df.columns):
            h.set_column(j, j, max(11, min(42, len(str(col)) + 4)))
        for i, fila in enumerate(df.itertuples(index=False), start=1):
            for j, (col, v) in enumerate(zip(df.columns, fila)):
                if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
                    continue
                f = formatos.get(col)
                if isinstance(v, pd.Timestamp):
                    h.write_datetime(i, j, v.to_pydatetime(), fec)
                elif isinstance(v, (int, float)) and f is not None:
                    h.write_number(i, j, float(v), f)
                else:
                    h.write(i, j, v if isinstance(v, (int, float)) else str(v))
        h.freeze_panes(1, 0)
        if len(df):
            h.autofilter(0, 0, len(df), len(df.columns) - 1)

    monedas = {c: sol for c in ("Materia prima", "Merma", "Mano de obra", "Terceros", "Indirectos (CIF)", "Costo total",
                                "Costo unitario", "Venta (sin IGV)", "Margen", "Monto", "Asignado", "Costo",
                                "Costo unit.", "Tarifa/h", "Valor del desvío", "Total")}
    monedas.update({"Margen %": pct, "% de la base": pct, "Desvío %": pct, "Horas MO": num, "Base": num,
                    "Requerida": num, "Consumida": num, "Usada": num, "Horas": num, "Cantidad": num})
    hoja("Costo por OT", res.por_ot, monedas)
    hoja("Por centro de costo", res.por_proceso, monedas)
    hoja("Asignación CIF", res.asignacion, monedas)
    hoja("Materia prima", res.materiales, monedas)
    hoja("Mano de obra", res.mano_obra, monedas)
    hoja("Terceros", res.terceros, monedas)
    hoja("Desvíos de consumo", res.desvios, monedas)
    libro.close()
    return salida.getvalue()


def pdf_costo_ot(res: Resultado, codigo: str, pedido: Pedido, hoy: date, demo: bool = False) -> bytes:
    """El reporte «Costos de orden de trabajo», con CIF, costo unitario y margen."""
    from trazabilidad.reportes import Documento, fecha_corta, soles

    fila = res.por_ot[res.por_ot["OT"] == codigo].iloc[0]
    det = detalle_ot(res, codigo)
    doc = Documento("COSTO DE ORDEN DE TRABAJO", f"OT {codigo} · {pedido.cliente}", "P", demo)
    doc.add_page()
    tarjetas = [("Costo total", soles(fila["Costo total"]), f"periodo: {res.periodo}"),
                ("Costo unitario", soles(fila["Costo unitario"]), f"{int(fila['Unidades'])} unidades"),
                ("Venta (sin IGV)", soles(fila["Venta (sin IGV)"]) if pd.notna(fila["Venta (sin IGV)"]) else "-", ""),
                ("Margen", f"{fila['Margen %']:.1%}" if pd.notna(fila["Margen %"]) else "-",
                 soles(fila["Margen"]) if pd.notna(fila["Margen"]) else "")]
    ancho = (doc.w - 28 - 3 * 4) / 4
    y = doc.get_y()
    for i, (a, b, c) in enumerate(tarjetas):
        doc.tarjeta_dato(14 + i * (ancho + 4), y, ancho, a, b, c)
    doc.set_y(y + 25)
    doc.set_font("Helvetica", "", 9)
    from trazabilidad.reportes import t as lat
    doc.multi_cell(0, 5, lat(f"Producto: {pedido.productos} · Emitido: {fecha_corta(hoy)} · "
                             f"Base de asignación de CIF: {BASES[res.base]}"), new_x="LMARGIN", new_y="NEXT")

    doc.seccion("Materia prima y auxiliares")
    m = det["materiales"]
    doc.tabla(("Proceso", "Material", "Consumo", "Merma", "Costo unit.", "Costo"),
              [(PROCESOS.get(r["Proceso"], r["Proceso"]), r["Material"], f"{r['Consumida']:,.2f} {r['UM'] or ''}",
                f"{(r['Merma'] or 0):,.2f}", soles(r["Costo unit."]), soles(r["Costo"])) for r in m.to_dict("records")],
              (22, 70, 26, 18, 22, 24), ("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"))
    if len(det["terceros"]):
        doc.seccion("Servicios de terceros")
        doc.tabla(("Proceso", "Proveedor", "Cantidad", "Costo unit.", "Costo"),
                  [(PROCESOS.get(r["Proceso"], r["Proceso"]), r["Proveedor"], f"{r['Cantidad']:,.0f}",
                    soles(r["Costo unit."]), soles(r["Costo"])) for r in det["terceros"].to_dict("records")],
                  (26, 82, 24, 26, 24),
                  ("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"))
    doc.seccion("Mano de obra directa")
    doc.tabla(("Proceso", "Personal", "Horas", "Tarifa/h", "Costo"),
              [(PROCESOS.get(r["Proceso"], r["Proceso"]), r["Personal"], f"{r['Horas']:,.2f}",
                soles(r["Tarifa/h"]), soles(r["Costo"])) for r in det["mano_obra"].to_dict("records")],
              (26, 82, 24, 26, 24),
              ("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"))
    if len(det["cif"]):
        doc.seccion("Costos indirectos asignados")
        doc.tabla(("Centro de costo", "Concepto", "% de la base", "Asignado"),
                  [(r["Centro"], r["Concepto"], f"{r['% de la base']:.1%}", soles(r["Asignado"]))
                   for r in det["cif"].to_dict("records")],
                  (56, 70, 28, 28), ("LEFT", "LEFT", "RIGHT", "RIGHT"))
    return bytes(doc.output())
