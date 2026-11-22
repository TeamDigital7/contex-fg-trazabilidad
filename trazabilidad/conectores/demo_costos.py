"""Costos de demostración, con la forma de la liquidación del ERP de Contex (HDSOFT).

Por cada pedido que ya pasó por planta: consumo de materia prima por proceso
(con lo que pedía la ficha técnica, lo realmente consumido y la merma), horas de
mano de obra interna (corte, arreglos, limpieza), órdenes de servicio a talleres
externos (bordado, estampado, confección) y los gastos indirectos del mes por
centro de costo. Las cifras son FICTICIAS pero de un orden de magnitud creíble.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

import pandas as pd

from trazabilidad.conectores.base import Tablas
from trazabilidad.costos import TablasCosto

# Ficha técnica por prenda: (proceso, código, material, UM, cantidad por prenda, costo unitario S/)
FICHAS = {
    "Chaleco drill naranja": [
        ("COR", "1010010051", "DRILL 100% POLIÉSTER NARANJA", "MTS", 0.85, 9.80),
        ("CNF", "2022020009", "CINTA REFLECTIVA 2\" ECONÓMICA", "MTS", 2.20, 2.49),
        ("CNF", "2011040060", "CIERRE NYLON NARANJA", "UND", 1.0, 0.81),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
        ("CNF", "2023020010", "RIBETE NARANJA", "MTS", 1.6, 0.15),
    ],
    "Pantalón drill azul marino": [
        ("COR", "1010010014", "DRILL NUEVO MUNDO ART 770 AZUL MARINO", "MTS", 1.25, 11.20),
        ("CNF", "2011040071", "CIERRE METÁLICO 7\" AZUL", "UND", 1.0, 0.95),
        ("CNF", "2024020001", "BOTÓN METÁLICO NACIONAL", "UND", 1.0, 0.15),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
    ],
    "Pantalón jean 14 oz industrial": [
        ("COR", "1010030008", "DENIM 14 OZ ÍNDIGO", "MTS", 1.30, 14.50),
        ("CNF", "2011040071", "CIERRE METÁLICO 7\" AZUL", "UND", 1.0, 0.95),
        ("CNF", "2024020003", "REMACHES Y BOTÓN JEAN", "UND", 1.0, 0.42),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
    ],
    "Polo piqué blanco con logo": [
        ("COR", "1010020011", "PIQUÉ 24/1 BLANCO", "KGS", 0.24, 27.50),
        ("CNF", "1010020080", "RIB DOBLE FIJADO 20/1 BLANCO", "KGS", 0.03, 26.00),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
    ],
    "Polo piqué azul con bordado": [
        ("COR", "1010020015", "PIQUÉ 24/1 AZUL", "KGS", 0.24, 28.40),
        ("CNF", "1010020081", "RIB DOBLE FIJADO 20/1 AZUL", "KGS", 0.03, 26.00),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
    ],
    "Overol drill gris con cinta reflectiva": [
        ("COR", "1010010090", "DRILL TECNOLOGÍA GRIS", "MTS", 2.40, 12.30),
        ("CNF", "2022020014", "CINTA REFLECTIVA 2\" 3M", "MTS", 3.20, 4.10),
        ("CNF", "2011040054", "CIERRE TRACTOR 60 CM GRIS", "UND", 1.0, 1.95),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
    ],
    "Casaca térmica con reflectivo": [
        ("COR", "1010040021", "TASLAN IMPERMEABLE AZUL", "MTS", 1.60, 15.80),
        ("COR", "1010040030", "POLAR ÁGUILA AZUL MARINO", "MTS", 1.10, 12.40),
        ("CNF", "2022020014", "CINTA REFLECTIVA 2\" 3M", "MTS", 1.80, 4.10),
        ("CNF", "2011040054", "CIERRE TRACTOR 60 CM", "UND", 1.0, 1.95),
    ],
    "Camisa drill beige manga larga": [
        ("COR", "1010010101", "DRILL LIVIANO BEIGE", "MTS", 1.45, 9.10),
        ("CNF", "2024020010", "BOTONES CAMISA x 9", "UND", 1.0, 0.36),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
    ],
    "Camisa oxford celeste manga larga": [
        ("COR", "1010050007", "OXFORD CELESTE", "MTS", 1.50, 10.40),
        ("CNF", "2024020010", "BOTONES CAMISA x 9", "UND", 1.0, 0.36),
        ("CNF", "2011030004", "ETIQUETAS TALLAS", "UND", 1.0, 0.03),
    ],
}

# Servicios de terceros por prenda: (proceso, taller, costo por prenda S/)
SERVICIOS = {
    "Chaleco drill naranja": [("CNF", "Confecciones Rímac E.I.R.L. (demo)", 8.50)],
    "Pantalón drill azul marino": [("CNF", "Taller Textil San Martín (demo)", 11.00)],
    "Pantalón jean 14 oz industrial": [("CNF", "Taller Textil San Martín (demo)", 12.50),
                                       ("LAV", "Lavandería Industrial Ate (demo)", 3.20)],
    "Polo piqué blanco con logo": [("EST", "Estampados Lima Norte (demo)", 2.10),
                                   ("CNF", "Confecciones Rímac E.I.R.L. (demo)", 6.20)],
    "Polo piqué azul con bordado": [("BOR", "Bordados Torres (demo)", 2.88),
                                    ("CNF", "Confecciones Rímac E.I.R.L. (demo)", 6.20)],
    "Overol drill gris con cinta reflectiva": [("CNF", "Taller Textil San Martín (demo)", 19.50)],
    "Casaca térmica con reflectivo": [("BOR", "Bordados Torres (demo)", 3.73),
                                      ("CNF", "Confecciones Rímac E.I.R.L. (demo)", 24.00)],
    "Camisa drill beige manga larga": [("BOR", "Bordados Torres (demo)", 2.88),
                                       ("CNF", "Confecciones Rímac E.I.R.L. (demo)", 10.50)],
    "Camisa oxford celeste manga larga": [("BOR", "Bordados Torres (demo)", 2.88),
                                          ("CNF", "Confecciones Rímac E.I.R.L. (demo)", 11.00)],
}

PERSONAL = {
    "COR": ["Herrera Guevara, Carlos (demo)", "Avilés Ortiz, Angler (demo)", "García Castro, Claudio (demo)"],
    "ARR": ["Trujillo Zambrano, Jesús (demo)"],
    "ACA": ["Quispe Mamani, Rosa (demo)"],
}
TARIFAS = {"COR": 9.50, "ARR": 8.20, "ACA": 7.40}  # S/ por hora (tabla maestra)
HORAS_POR_PRENDA = {"COR": 0.035, "ACA": 0.018}

# Gastos indirectos de un mes típico: (centro, concepto, monto S/)
CIF_MES = [
    ("COR", "Depreciación cortadora y ploteo", 420.0),
    ("COR", "Software de tizado (licencia)", 310.0),
    ("COR", "Energía taller de corte", 260.0),
    ("ARR", "Mantenimiento máquinas de coser", 180.0),
    ("PLA", "Alquiler de planta y almacén", 3200.0),
    ("PLA", "Jefatura de producción", 2800.0),
    ("PLA", "Movilidad propia y conductor", 1150.0),
    ("PLA", "Energía y agua (general)", 640.0),
    ("PLA", "Control de calidad (SIG)", 900.0),
]

ORDEN = ["recibido", "produccion", "inspeccion", "despacho", "entregado"]


def _cuando(dia: date, hora: int = 10) -> datetime:
    return datetime.combine(dia, time(hora))


def total_pedido(p: dict) -> int:
    return int(p.get("_unidades") or 0)


def generar_costos(tablas: Tablas, hoy: date | None = None) -> TablasCosto:
    hoy = hoy or date.today()
    azar = random.Random(77)
    lineas = tablas.lineas
    mp, mo, te = [], [], []
    unidades = lineas.groupby("codigo_pedido")["cantidad"].sum().to_dict()
    for p in tablas.pedidos.to_dict("records"):
        p["_unidades"] = unidades.get(p["codigo"], 0)
        etapa = ORDEN.index(p["etapa"])
        if etapa == 0:
            continue  # recién recibido: todavía no hay consumo
        avance = float(p["avance_produccion"]) if p["etapa"] == "produccion" else 1.0
        inicio = pd.to_datetime(p["fecha_pedido"]).date() + timedelta(days=3)
        ventanas = {"COR": 1, "BOR": 5, "EST": 5, "CNF": 7, "LAV": 12, "ARR": 15, "ACA": 16}
        umbral = {"COR": 0.0, "BOR": 0.4, "EST": 0.4, "CNF": 0.55, "LAV": 0.9, "ACA": 0.95}

        def toca(proc):
            dia = inicio + timedelta(days=ventanas[proc])
            return avance >= umbral.get(proc, 1.0) and dia <= hoy, dia

        for ln in lineas[lineas["codigo_pedido"] == p["codigo"]].to_dict("records"):
            prod, cant = ln["producto"], int(ln["cantidad"])
            for proc, cod, desc, um, por_prenda, costo in FICHAS.get(prod, []):
                ok, dia = toca(proc)
                if not ok:
                    continue
                requerida = round(por_prenda * cant, 2)
                # Un pedido con no conformes recortó piezas: consume más tela de la que pedía la ficha
                nc = int(p.get("no_conformes") or 0)
                exceso = (1 + 0.07 * nc) if proc == "COR" else 1.0  # más no conformes, más tela recortada
                consumida = round(requerida * azar.uniform(0.96, 1.05) * exceso, 2)
                if um == "UND":  # botones, cierres, etiquetas: se cuentan enteros
                    requerida, consumida = round(requerida), round(requerida * azar.uniform(1.0, 1.03))
                merma = round(consumida * azar.uniform(0.02, 0.07), 2) if proc == "COR" else 0.0
                mp.append({"codigo_pedido": p["codigo"], "fecha": _cuando(dia), "proceso": proc, "codigo": cod,
                           "descripcion": desc, "um": um, "cant_requerida": requerida,
                           "cant_consumida": consumida, "cant_merma": merma,
                           "costo_unitario": round(costo * azar.uniform(0.97, 1.04), 2)})
            for proc, taller, costo in SERVICIOS.get(prod, []):
                ok, dia = toca(proc)
                if ok:
                    te.append({"codigo_pedido": p["codigo"], "fecha": _cuando(dia), "proceso": proc,
                               "proveedor": taller, "cantidad": cant, "costo_unitario": costo})
            # Las prendas observadas vuelven al taller externo para rehacer la costura
            if int(p.get("no_conformes") or 0) and etapa >= 2 and SERVICIOS.get(prod):
                proc, taller, costo = next(s_ for s_ in SERVICIOS[prod] if s_[0] == "CNF")
                dia = inicio + timedelta(days=ventanas["ARR"])
                if dia <= hoy:
                    te.append({"codigo_pedido": p["codigo"], "fecha": _cuando(dia), "proceso": "ARR",
                               "proveedor": taller, "cantidad": round(cant * 0.04 * int(p["no_conformes"])),
                               "costo_unitario": costo})
            for proc in ("COR", "ACA"):
                ok, dia = toca(proc)
                if not ok:
                    continue
                horas_total = HORAS_POR_PRENDA[proc] * cant * azar.uniform(0.9, 1.25)
                equipo = PERSONAL[proc]
                for persona in equipo:
                    mo.append({"codigo_pedido": p["codigo"], "fecha": _cuando(dia, 9), "proceso": proc,
                               "personal": persona, "horas": round(horas_total / len(equipo), 2),
                               "tarifa_hora": None})
        # Reprocesos: los pedidos con no conformes pasan por el taller de arreglos
        if int(p.get("no_conformes") or 0) and etapa >= 2:
            dia = inicio + timedelta(days=ventanas["ARR"])
            if dia <= hoy:
                mo.append({"codigo_pedido": p["codigo"], "fecha": _cuando(dia, 14), "proceso": "ARR",
                           "personal": PERSONAL["ARR"][0],
                           "horas": round(int(p["no_conformes"]) * total_pedido(p) * 0.05 * azar.uniform(0.9, 1.1), 2),
                           "tarifa_hora": None})

    cols_mp = ["codigo_pedido", "fecha", "proceso", "codigo", "descripcion", "um", "cant_requerida",
               "cant_consumida", "cant_merma", "costo_unitario"]
    meses = sorted({r["fecha"].strftime("%Y-%m") for r in mp + mo + te})
    cif = [{"periodo": m, "centro": c, "concepto": concepto, "monto": round(monto * azar.uniform(0.95, 1.08), 2)}
           for m in meses for c, concepto, monto in CIF_MES]
    return TablasCosto(
        materiales=pd.DataFrame(mp, columns=cols_mp),
        mano_obra=pd.DataFrame(mo, columns=["codigo_pedido", "fecha", "proceso", "personal", "horas", "tarifa_hora"]),
        terceros=pd.DataFrame(te, columns=["codigo_pedido", "fecha", "proceso", "proveedor", "cantidad",
                                           "costo_unitario"]),
        cif=pd.DataFrame(cif, columns=["periodo", "centro", "concepto", "monto"]),
        tarifas=dict(TARIFAS),
    )
