"""Datos de demostración: pedidos ficticios con fechas relativas a HOY.

Las fechas se calculan desde el día en que se abre la app, así la demo nunca
envejece: siempre hay pedidos en producción, alguno en riesgo y entregas
recientes. La semilla es fija, así que dos personas ven exactamente lo mismo.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

import pandas as pd

from trazabilidad.conectores.base import Conector, Tablas
from trazabilidad.modelo import SUBETAPAS_PRODUCCION

CLIENTES = [
    "Minera Los Andes S.A.C. (demo)",
    "Constructora Pacífico S.A.C. (demo)",
    "Pesquera Mar Azul S.A.C. (demo)",
    "Hidroeléctrica Cumbre S.A. (demo)",
    "Eléctrica del Sur S.A. (demo)",
    "Distribuidora Norte E.I.R.L. (demo)",
    "Agroindustrias Valle Verde S.A. (demo)",
]

# (código, cliente, productos [(producto, cantidad)], etapa, días desde hoy a la entrega, extra)
PEDIDOS = [
    ("PED-2026-0005", 0, [("Casaca térmica con reflectivo", 120)], "entregado", -38, {"encuesta": 4.6}),
    ("PED-2026-0006", 4, [("Overol drill gris con cinta reflectiva", 90)], "entregado", -24, {"encuesta": 4.2, "tarde": 3}),
    ("PED-2026-0007", 2, [("Polo piqué blanco con logo", 300)], "entregado", -18, {"encuesta": 4.9}),
    ("PED-2026-0008", 0, [("Pantalón drill azul marino", 40), ("Chaleco drill naranja", 32)], "entregado", -9, {"encuesta": 5.0}),
    ("PED-2026-0009", 5, [("Polo piqué blanco con logo", 250)], "entregado", -4, {}),
    ("PED-2026-0010", 3, [("Pantalón drill azul marino", 40), ("Chaleco drill naranja", 40)], "despacho", 2, {"despachado": 22}),
    ("PED-2026-0011", 4, [("Overol drill gris con cinta reflectiva", 100)], "despacho", 5, {}),
    ("PED-2026-0012", 1, [("Chaleco drill naranja", 130), ("Pantalón jean 14 oz industrial", 120)], "inspeccion", 6, {"no_conformes": 1}),
    ("PED-2026-0016", 6, [("Camisa drill beige manga larga", 60)], "inspeccion", 9, {}),
    ("PED-2026-0014", 2, [("Polo piqué blanco con logo", 400)], "produccion", 7, {"avance": 0.30}),
    ("PED-2026-0013", 0, [("Chaleco drill naranja", 150), ("Pantalón drill azul marino", 150)], "produccion", 17, {"avance": 0.55}),
    ("PED-2026-0015", 6, [("Camisa oxford celeste manga larga", 80)], "produccion", 29, {"avance": 0.20}),
    ("PED-2026-0017", 3, [("Casaca térmica con reflectivo", 70)], "produccion", 24, {"avance": 0.80}),
    ("PED-2026-0018", 1, [("Overol drill gris con cinta reflectiva", 200)], "recibido", 34, {}),
    ("PED-2026-0019", 5, [("Polo piqué azul con bordado", 180)], "recibido", 21, {}),
]

RESPONSABLES = {
    "recibido": "Ana Torres · Comercial",
    "produccion": "Luis Ramos · Jefe de planta",
    "inspeccion": "Carla Mendoza · Calidad",
    "despacho": "Jorge Salas · Almacén",
    "entregado": "Ana Torres · Comercial",
}


def _a_las(dia: date, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(dia, time(hora, minuto))


def generar_tablas(hoy: date | None = None) -> Tablas:
    hoy = hoy or date.today()
    azar = random.Random(2026)
    filas_pedidos, filas_lineas, filas_eventos = [], [], []

    for codigo, i_cliente, productos, etapa, dias_entrega, extra in PEDIDOS:
        entrega = hoy + timedelta(days=dias_entrega)
        pedido = entrega - timedelta(days=azar.randint(24, 32))
        pedido = min(pedido, hoy - timedelta(days=1))  # un pedido nunca es del futuro
        total = sum(c for _, c in productos)
        entregado_el = None
        if etapa == "entregado":
            entregado_el = entrega + timedelta(days=extra.get("tarde", -azar.randint(0, 2)))

        avance = {"recibido": 0.0, "produccion": extra.get("avance", 0.0)}.get(etapa, 1.0)
        filas_pedidos.append({
            "codigo": codigo,
            "cliente": CLIENTES[i_cliente],
            "etapa": etapa,
            "fecha_pedido": pedido,
            "fecha_entrega": entrega,
            "avance_produccion": avance,
            "no_conformes": extra.get("no_conformes", 0),
            "cantidad_despachada": extra.get("despachado", total if etapa == "entregado" else 0),
            "liberado": etapa in ("despacho", "entregado"),
            "encuesta": extra.get("encuesta"),
            "fecha_entregado": entregado_el,
        })
        for producto, cantidad in productos:
            filas_lineas.append({"codigo_pedido": codigo, "producto": producto, "cantidad": cantidad})

        filas_eventos.extend(_eventos(codigo, etapa, pedido, hoy, avance, total, extra, entregado_el))

    return Tablas(pd.DataFrame(filas_pedidos), pd.DataFrame(filas_lineas), pd.DataFrame(filas_eventos))


def _eventos(codigo, etapa, pedido, hoy, avance, total, extra, entregado_el) -> list[dict]:
    """El registro ISO que deja cada etapa, hasta donde llegó el pedido."""
    orden = ["recibido", "produccion", "inspeccion", "despacho", "entregado"]
    hasta = orden.index(etapa)
    ev = []

    def anotar(dia, hora, et, clausula, texto, evidencia=""):
        if dia <= hoy:
            ev.append({"codigo_pedido": codigo, "fecha": _a_las(dia, hora), "etapa": et,
                       "clausula": clausula, "descripcion": texto,
                       "responsable": RESPONSABLES[et], "evidencia": evidencia})

    anotar(pedido, 9, "recibido", "ISO 8.2.3", "Orden de compra recibida y requisitos revisados.", f"OC-{codigo[-4:]}.pdf")
    anotar(pedido + timedelta(days=1), 15, "recibido", "ISO 8.4", "Telas e insumos solicitados a proveedor homologado.", "Orden de compra de insumos")
    if hasta >= 1:
        inicio = pedido + timedelta(days=3)
        anotar(inicio, 8, "produccion", "ISO 8.5.1", "Inicio de corte según ficha técnica aprobada.", "Ficha técnica v2")
        hechas = len(SUBETAPAS_PRODUCCION) if hasta > 1 else int(avance * len(SUBETAPAS_PRODUCCION))
        for n, sub in enumerate(SUBETAPAS_PRODUCCION[1:hechas + 1], start=1):
            anotar(inicio + timedelta(days=3 * n), 10, "produccion", "ISO 8.5.1",
                   f"{sub}: inicio de etapa. Control de proceso conforme.")
    if hasta >= 2:
        fin_prod = pedido + timedelta(days=16)
        anotar(fin_prod, 11, "inspeccion", "ISO 8.6", f"Inspección final por muestreo AQL 2.5 sobre {total} prendas.", "Registro de inspección")
        if extra.get("no_conformes"):
            anotar(fin_prod, 16, "inspeccion", "ISO 8.7",
                   f"{extra['no_conformes']} salida(s) no conforme(s): costura irregular. En reproceso.", "Informe de no conformidad")
    if hasta >= 3:
        anotar(pedido + timedelta(days=18), 9, "inspeccion", "ISO 8.6", "Lote liberado por Calidad.", "Certificado de conformidad")
        if extra.get("despachado"):
            anotar(pedido + timedelta(days=19), 14, "despacho", "Guía · factura",
                   f"Entrega parcial: {extra['despachado']} de {total} prendas.", "Guía de remisión T001-0458")
    if hasta >= 4 and entregado_el:
        anotar(entregado_el, 12, "despacho", "Guía · factura", "Pedido completo entregado y facturado.", "Factura F001-1290")
        anotar(entregado_el, 17, "entregado", "ISO 9.1.2", "Conformidad de recepción firmada por el cliente.", "Acta de entrega")
        if extra.get("encuesta") is not None:
            anotar(entregado_el + timedelta(days=3), 10, "entregado", "ISO 9.1.2",
                   f"Encuesta de satisfacción respondida: {extra['encuesta']:.1f} / 5.")
    return ev


class ConectorDemo(Conector):
    nombre = "Datos de demostración"
    es_demo = True

    def __init__(self, hoy: date | None = None):
        self.hoy = hoy

    def leer_tablas(self) -> Tablas:
        return generar_tablas(self.hoy)
