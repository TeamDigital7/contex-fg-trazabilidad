"""Conector a una base de datos SQL (PostgreSQL, MySQL, SQL Server, Oracle...).

Se configura en Secrets con una URL de SQLAlchemy y TRES consultas. Las
consultas pueden ser tan complejas como haga falta (joins, vistas): lo único que
importa es que devuelvan las columnas que pide `base.COLUMNAS`. Así no hay que
cambiar código cuando se conecte la base del cliente: solo escribir sus SELECT.
"""

from __future__ import annotations

import pandas as pd

from trazabilidad.conectores.base import Conector, ErrorDeDatos, Tablas


class ConectorSQL(Conector):
    nombre = "Base de datos SQL"

    def __init__(self, url: str, consultas: dict[str, str]):
        if not url:
            raise ErrorDeDatos("Falta `url` en la sección [datos] de Secrets.")
        faltan = [t for t in ("pedidos", "lineas", "eventos") if not consultas.get(t)]
        if faltan:
            raise ErrorDeDatos("Faltan consultas en [datos.consultas]: " + ", ".join(faltan))
        self.url = url
        self.consultas = consultas

    def leer_tablas(self) -> Tablas:
        try:
            from sqlalchemy import create_engine, text
        except ImportError as exc:  # pragma: no cover
            raise ErrorDeDatos("Falta instalar sqlalchemy (está en requirements.txt).") from exc
        motor = create_engine(self.url, pool_pre_ping=True)
        try:
            with motor.connect() as cx:
                tablas = {t: pd.read_sql(text(q), cx) for t, q in self.consultas.items()
                          if t in ("pedidos", "lineas", "eventos")}
        finally:
            motor.dispose()
        return Tablas(tablas["pedidos"], tablas["lineas"], tablas["eventos"])

    def leer_costos(self):
        """Las consultas costos_* de [datos.consultas] (opcionales). Sin ellas: None."""
        from trazabilidad.costos import TablasCosto
        claves = ("costos_materiales", "costos_mano_obra", "costos_terceros", "costos_cif")
        if not all(self.consultas.get(c) for c in claves):
            return None
        from sqlalchemy import create_engine, text
        motor = create_engine(self.url, pool_pre_ping=True)
        try:
            with motor.connect() as cx:
                t = {c: pd.read_sql(text(self.consultas[c]), cx) for c in claves}
        finally:
            motor.dispose()
        return TablasCosto(t["costos_materiales"], t["costos_mano_obra"], t["costos_terceros"], t["costos_cif"])
