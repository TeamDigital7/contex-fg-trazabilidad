"""Contrato de un conector: entrega TRES tablas y el mapeo a pedidos es uno solo.

Cualquier fuente (demo, SQL, Excel...) devuelve las mismas tres tablas con las
mismas columnas. `pedidos_desde_tablas` las convierte en objetos `Pedido`, así
que los datos de demostración y los reales pasan por el MISMO camino: lo que se
le enseña al cliente con la demo es exactamente lo que verá con sus datos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from trazabilidad.modelo import Evento, Linea, Pedido, normalizar_etapa

# Columnas que cada tabla tiene que traer. Las marcadas como opcionales pueden faltar.
COLUMNAS = {
    "pedidos": {
        "obligatorias": ["codigo", "cliente", "etapa", "fecha_pedido", "fecha_entrega"],
        "opcionales": ["avance_produccion", "no_conformes", "cantidad_despachada",
                       "liberado", "encuesta", "fecha_entregado"],
    },
    "lineas": {
        "obligatorias": ["codigo_pedido", "producto", "cantidad"],
        "opcionales": [],
    },
    "eventos": {
        "obligatorias": ["codigo_pedido", "fecha", "etapa", "descripcion"],
        "opcionales": ["clausula", "responsable", "evidencia"],
    },
}


class ErrorDeDatos(Exception):
    """La fuente respondió, pero con una forma que la app no puede leer."""


@dataclass
class Tablas:
    pedidos: pd.DataFrame
    lineas: pd.DataFrame
    eventos: pd.DataFrame


class Conector(ABC):
    nombre: str = "conector"
    es_demo: bool = False

    @abstractmethod
    def leer_tablas(self) -> Tablas:
        """Lee las tres tablas de la fuente."""

    def probar(self) -> str:
        """Comprueba la conexión. Devuelve un texto para la pantalla o levanta."""
        t = self.leer_tablas()
        return f"{len(t.pedidos)} pedidos · {len(t.lineas)} líneas · {len(t.eventos)} eventos"


# --- Mapeo único tablas -> pedidos ------------------------------------------------

def _columnas_faltantes(df: pd.DataFrame, tabla: str) -> list[str]:
    presentes = {str(c).strip().lower() for c in df.columns}
    return [c for c in COLUMNAS[tabla]["obligatorias"] if c not in presentes]


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _fecha(valor) -> date | None:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    try:
        ts = pd.to_datetime(valor)
    except (ValueError, TypeError):
        return None
    if pd.isna(ts):
        return None
    return ts.date()


def _fecha_hora(valor) -> datetime | None:
    try:
        ts = pd.to_datetime(valor)
    except (ValueError, TypeError):
        return None
    return None if pd.isna(ts) else ts.to_pydatetime()


def _num(valor, defecto=0.0) -> float:
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return defecto
    return defecto if pd.isna(n) else n


def _texto(valor) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def _si(valor) -> bool:
    return _texto(valor).lower() in {"1", "true", "si", "sí", "yes", "x", "s"}


def pedidos_desde_tablas(tablas: Tablas) -> tuple[list[Pedido], list[str]]:
    """Convierte las tres tablas en pedidos. Devuelve (pedidos, avisos).

    Una fila mala no tumba la pantalla: se salta y se explica en los avisos.
    Una columna obligatoria que falta sí levanta, porque ahí no hay nada que leer.
    """
    avisos: list[str] = []
    pedidos_df = _normalizar(tablas.pedidos)
    lineas_df = _normalizar(tablas.lineas)
    eventos_df = _normalizar(tablas.eventos)

    for nombre, df in (("pedidos", pedidos_df), ("lineas", lineas_df), ("eventos", eventos_df)):
        faltan = _columnas_faltantes(df, nombre)
        if faltan:
            raise ErrorDeDatos(f"A la tabla '{nombre}' le faltan columnas: {', '.join(faltan)}")

    lineas_por_pedido: dict[str, list[Linea]] = {}
    for fila in lineas_df.to_dict("records"):
        codigo = _texto(fila.get("codigo_pedido"))
        lineas_por_pedido.setdefault(codigo, []).append(
            Linea(producto=_texto(fila.get("producto")), cantidad=int(_num(fila.get("cantidad"))))
        )

    eventos_por_pedido: dict[str, list[Evento]] = {}
    for fila in eventos_df.to_dict("records"):
        cuando = _fecha_hora(fila.get("fecha"))
        if cuando is None:
            continue
        codigo = _texto(fila.get("codigo_pedido"))
        eventos_por_pedido.setdefault(codigo, []).append(Evento(
            fecha=cuando,
            etapa=normalizar_etapa(fila.get("etapa")) or _texto(fila.get("etapa")),
            clausula=_texto(fila.get("clausula")),
            descripcion=_texto(fila.get("descripcion")),
            responsable=_texto(fila.get("responsable")),
            evidencia=_texto(fila.get("evidencia")),
        ))

    pedidos: list[Pedido] = []
    vistos: set[str] = set()
    for i, fila in enumerate(pedidos_df.to_dict("records"), start=2):
        codigo = _texto(fila.get("codigo"))
        etapa = normalizar_etapa(fila.get("etapa"))
        fecha_pedido = _fecha(fila.get("fecha_pedido"))
        fecha_entrega = _fecha(fila.get("fecha_entrega"))
        if not codigo:
            avisos.append(f"Fila {i}: pedido sin código, no se muestra.")
            continue
        if codigo in vistos:
            avisos.append(f"{codigo}: aparece dos veces; se muestra la primera.")
            continue
        if not etapa:
            avisos.append(f"{codigo}: etapa '{_texto(fila.get('etapa'))}' no reconocida.")
            continue
        if fecha_pedido is None or fecha_entrega is None:
            avisos.append(f"{codigo}: falta la fecha de pedido o de entrega.")
            continue
        vistos.add(codigo)
        encuesta = fila.get("encuesta")
        pedidos.append(Pedido(
            codigo=codigo,
            cliente=_texto(fila.get("cliente")),
            etapa=etapa,
            fecha_pedido=fecha_pedido,
            fecha_entrega=fecha_entrega,
            lineas=lineas_por_pedido.get(codigo, []),
            avance_produccion=min(max(_num(fila.get("avance_produccion")), 0.0), 1.0),
            no_conformes=int(_num(fila.get("no_conformes"))),
            cantidad_despachada=int(_num(fila.get("cantidad_despachada"))),
            liberado=_si(fila.get("liberado")),
            encuesta=None if _texto(encuesta) == "" else _num(encuesta, None),
            fecha_entregado=_fecha(fila.get("fecha_entregado")),
            eventos=sorted(eventos_por_pedido.get(codigo, []), key=lambda e: e.fecha),
        ))
        if not pedidos[-1].lineas:
            avisos.append(f"{codigo}: no tiene líneas de producto.")
    return pedidos, avisos
