"""Elige el conector según la configuración (Secrets). Sin configuración: demo."""

from __future__ import annotations

from collections.abc import Mapping

from trazabilidad.conectores.base import COLUMNAS, Conector, ErrorDeDatos, Tablas, pedidos_desde_tablas
from trazabilidad.conectores.demo import ConectorDemo
from trazabilidad.conectores.sql import ConectorSQL

__all__ = ["COLUMNAS", "Conector", "ConectorDemo", "ConectorSQL", "ErrorDeDatos",
           "Tablas", "obtener_conector", "pedidos_desde_tablas"]


def obtener_conector(config: Mapping | None) -> Conector:
    """`config` es la sección [datos] de Secrets.

    - sin sección, o `conector = "demo"` -> datos de demostración
    - `conector = "sql"` -> base de datos con `url` y [datos.consultas]
    """
    config = dict(config or {})
    tipo = str(config.get("conector", "demo")).strip().lower()
    if tipo in ("", "demo"):
        return ConectorDemo()
    if tipo == "sql":
        return ConectorSQL(str(config.get("url", "")), dict(config.get("consultas", {}) or {}))
    raise ErrorDeDatos(f"Conector '{tipo}' no reconocido. Usa 'demo' o 'sql'.")
