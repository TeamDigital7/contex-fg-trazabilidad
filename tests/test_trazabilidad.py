"""Pruebas: modelo, mapeo de tablas, conectores y la app entera (AppTest).

python -m pytest tests -q      o      python tests/test_trazabilidad.py
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from trazabilidad import vistas  # noqa: E402
from trazabilidad.conectores import (ConectorDemo, ConectorSQL, ErrorDeDatos, Tablas,  # noqa: E402
                                     obtener_conector, pedidos_desde_tablas)
from trazabilidad.modelo import (ETAPAS, Linea, Pedido, en_riesgo, etiqueta,  # noqa: E402
                                 indicadores, normalizar_etapa, por_etapa)

HOY = date(2026, 11, 22)


def pedido(**kw) -> Pedido:
    base = dict(codigo="PED-1", cliente="Cliente", etapa="produccion",
                fecha_pedido=HOY - timedelta(days=10), fecha_entrega=HOY + timedelta(days=30),
                lineas=[Linea("Polo", 100)])
    base.update(kw)
    return Pedido(**base)


class Modelo(unittest.TestCase):
    def test_riesgo_se_proyecta_con_el_avance(self):
        self.assertTrue(en_riesgo(pedido(avance_produccion=0.3, fecha_entrega=HOY + timedelta(days=7)), HOY))
        self.assertFalse(en_riesgo(pedido(avance_produccion=0.9, fecha_entrega=HOY + timedelta(days=7)), HOY))

    def test_etiquetas_por_etapa(self):
        self.assertEqual(etiqueta(pedido(etapa="inspeccion", no_conformes=2), HOY), ("2 no conforme(s)", "ambar"))
        self.assertEqual(etiqueta(pedido(etapa="despacho", cantidad_despachada=40), HOY), ("Entrega 40/100", "azul"))
        self.assertEqual(etiqueta(pedido(etapa="entregado", encuesta=4.5), HOY), ("Encuesta 4.5 / 5", "verde"))
        self.assertEqual(etiqueta(pedido(etapa="entregado"), HOY)[0], "Encuesta pendiente")
        self.assertEqual(etiqueta(pedido(fecha_entrega=HOY - timedelta(days=1)), HOY), ("Atrasado", "rojo"))

    def test_subetapa_sale_del_avance(self):
        self.assertEqual(pedido(avance_produccion=0.0).subetapa, "Corte")
        self.assertEqual(pedido(avance_produccion=0.55).subetapa, "Estampado / bordado")
        self.assertEqual(pedido(avance_produccion=1.0).subetapa, "Acabado y empaque")

    def test_entregado_viejo_sale_del_tablero(self):
        viejo = pedido(codigo="A", etapa="entregado", fecha_entregado=HOY - timedelta(days=45))
        reciente = pedido(codigo="B", etapa="entregado", fecha_entregado=HOY - timedelta(days=5))
        grupos = por_etapa([viejo, reciente], HOY)
        self.assertEqual([p.codigo for p in grupos["entregado"]], ["B"])

    def test_alias_de_etapa(self):
        self.assertEqual(normalizar_etapa("Producción"), "produccion")
        self.assertEqual(normalizar_etapa("CALIDAD"), "inspeccion")
        self.assertEqual(normalizar_etapa("otra cosa"), "")


class Mapeo(unittest.TestCase):
    def test_la_demo_cubre_todas_las_etapas_sin_avisos(self):
        pedidos, avisos = pedidos_desde_tablas(ConectorDemo(HOY).leer_tablas())
        self.assertEqual(avisos, [])
        grupos = por_etapa(pedidos, HOY)
        for etapa in ETAPAS:
            self.assertTrue(grupos[etapa.clave], etapa.clave)
        self.assertTrue(all(p.eventos for p in pedidos))

    def test_la_demo_no_envejece(self):
        for hoy in (HOY, HOY + timedelta(days=400)):
            pedidos, _ = pedidos_desde_tablas(ConectorDemo(hoy).leer_tablas())
            ind = indicadores(pedidos, hoy)
            self.assertGreater(ind["activos"], 5)
            self.assertTrue(por_etapa(pedidos, hoy)["entregado"])

    def test_columna_que_falta_se_nombra(self):
        t = ConectorDemo(HOY).leer_tablas()
        with self.assertRaisesRegex(ErrorDeDatos, "fecha_entrega"):
            pedidos_desde_tablas(Tablas(t.pedidos.drop(columns=["fecha_entrega"]), t.lineas, t.eventos))

    def test_fila_mala_se_salta_y_se_explica(self):
        t = ConectorDemo(HOY).leer_tablas()
        malo = t.pedidos.copy()
        malo.loc[0, "etapa"] = "inventada"
        malo = pd.concat([malo, malo.iloc[[1]]])  # código repetido
        pedidos, avisos = pedidos_desde_tablas(Tablas(malo, t.lineas, t.eventos))
        self.assertEqual(len(pedidos), len(t.pedidos) - 1)
        self.assertEqual(len(avisos), 2)

    def test_html_escapa_los_datos(self):
        p = pedido(cliente="<script>x</script> & Cía")
        html = vistas.tarjeta(p, HOY, "interno")
        self.assertNotIn("<script>", html)
        self.assertIn("&amp; Cía", html)


class ConectorSQLReal(unittest.TestCase):
    """El conector SQL se prueba contra un SQLite de verdad con las tablas de la demo."""

    def test_lee_lo_mismo_que_la_demo(self, ):
        import tempfile
        t = ConectorDemo(HOY).leer_tablas()
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "prod.db"
            with sqlite3.connect(ruta) as cx:
                t.pedidos.to_sql("pedidos", cx, index=False)
                t.lineas.to_sql("lineas", cx, index=False)
                t.eventos.to_sql("eventos", cx, index=False)
            conector = obtener_conector({"conector": "sql", "url": f"sqlite:///{ruta}", "consultas": {
                "pedidos": "SELECT * FROM pedidos", "lineas": "SELECT * FROM lineas",
                "eventos": "SELECT * FROM eventos"}})
            self.assertIsInstance(conector, ConectorSQL)
            reales, avisos = pedidos_desde_tablas(conector.leer_tablas())
        demo, _ = pedidos_desde_tablas(t)
        self.assertEqual(avisos, [])
        self.assertEqual([(p.codigo, p.etapa, p.cantidad_total, len(p.eventos)) for p in reales],
                         [(p.codigo, p.etapa, p.cantidad_total, len(p.eventos)) for p in demo])

    def test_config_incompleta_se_explica(self):
        with self.assertRaisesRegex(ErrorDeDatos, "url"):
            obtener_conector({"conector": "sql"})
        with self.assertRaisesRegex(ErrorDeDatos, "eventos"):
            obtener_conector({"conector": "sql", "url": "sqlite://", "consultas": {"pedidos": "x", "lineas": "y"}})
        self.assertIsInstance(obtener_conector(None), ConectorDemo)


class App(unittest.TestCase):
    """La app real. Se mira at.error además de at.exception."""

    def correr(self, **params):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
        for k, v in params.items():
            at.query_params[k] = v
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(at.error, [e.value for e in at.error])
        return at

    def html(self, at) -> str:
        return " ".join(m.value for m in at.markdown)

    def test_tablero(self):
        at = self.correr()
        texto = self.html(at)
        for etapa in ETAPAS:
            self.assertIn(vistas.esc(etapa.nombre), texto)
        self.assertIn("DATOS DE DEMOSTRACIÓN", texto)

    def test_vista_de_cliente_solo_ve_lo_suyo(self):
        at = self.correr(vista="Minera Los Andes S.A.C. (demo)")
        texto = self.html(at)
        self.assertIn("Minera Los Andes", texto)
        self.assertNotIn("Pesquera Mar Azul", texto)
        self.assertNotIn("Conexión de datos", [o for r in at.radio for o in r.options])

    def test_detalle(self):
        at = self.correr(pedido="PED-2026-0012")
        texto = self.html(at)
        self.assertIn("Registro", " ".join(s.value for s in at.subheader))
        self.assertIn("ISO 8.7", texto)

    def test_cliente_no_abre_pedidos_ajenos(self):
        at = self.correr(vista="Minera Los Andes S.A.C. (demo)", pedido="PED-2026-0012")
        self.assertNotIn("Constructora Pacífico", self.html(at))

    def test_lista_y_conexion(self):
        at = self.correr()
        for pagina in ("Lista de pedidos", "Conexión de datos"):
            at.radio[0].set_value(pagina).run()
            self.assertFalse(at.exception, at.exception)
            self.assertFalse(at.error, [e.value for e in at.error])


if __name__ == "__main__":
    unittest.main(verbosity=1)
