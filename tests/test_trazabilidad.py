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


class Reportes(unittest.TestCase):
    def setUp(self):
        from trazabilidad import reportes
        self.r = reportes
        self.pedidos, _ = pedidos_desde_tablas(ConectorDemo(HOY).leer_tablas())

    def test_proforma_pdf_con_totales(self):
        p = next(x for x in self.pedidos if x.codigo == "PED-2026-0012")
        self.assertTrue(p.con_precios)
        self.assertAlmostEqual(p.subtotal, 130 * 42.0 + 120 * 69.9)
        pdf = self.r.pdf_pedido(p, HOY, demo=True)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 3000)

    def test_sin_precios_tambien_sale(self):
        pdf = self.r.pdf_pedido(pedido(cliente="Señora — Ñandú “test”"), HOY)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_resumen_y_excel(self):
        import openpyxl, io
        self.assertTrue(self.r.pdf_resumen(self.pedidos, HOY, "Todos").startswith(b"%PDF"))
        libro = openpyxl.load_workbook(io.BytesIO(self.r.excel_resumen(self.pedidos, HOY, "Todos")))
        self.assertEqual(libro.sheetnames, ["Resumen", "Pedidos", "Productos", "Registro ISO"])
        self.assertEqual(libro["Pedidos"].max_row, len(self.pedidos) + 1)

    def test_historial_muestra_entregados_antiguos(self):
        corto = por_etapa(self.pedidos, HOY)["entregado"]
        todo = por_etapa(self.pedidos, HOY, None)["entregado"]
        self.assertGreater(len(todo), len(corto))


class FalsoMeta:
    """Imita la Cloud API: guarda cada petición y responde como Meta."""

    def __init__(self, fallar_documentos_con=None):
        self.peticiones = []
        self.fallar_documentos_con = fallar_documentos_con

    def __call__(self, req, timeout=None):
        import io, json, urllib.error
        cuerpo = req.data or b""
        self.peticiones.append((req.full_url, req.get_header("Content-type"), cuerpo,
                                req.get_header("Authorization")))
        if req.full_url.endswith("/media"):
            respuesta = {"id": f"media-{len(self.peticiones)}"}
        else:
            datos = json.loads(cuerpo)
            if datos["type"] == "document" and self.fallar_documentos_con:
                error = json.dumps({"error": {"code": self.fallar_documentos_con, "message": "Re-engagement"}})
                raise urllib.error.HTTPError(req.full_url, 400, "Bad", {}, io.BytesIO(error.encode()))
            respuesta = {"messages": [{"id": "wamid.1"}]}

        class R(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R(json.dumps(respuesta).encode())


class WhatsApp(unittest.TestCase):
    def setUp(self):
        from trazabilidad import whatsapp
        self.w = whatsapp
        self.pedidos, _ = pedidos_desde_tablas(ConectorDemo(HOY).leer_tablas())
        self.p = next(x for x in self.pedidos if x.codigo == "PED-2026-0012")
        self.docs = [whatsapp.Documento(b"%PDF-1", "Pedido.pdf", whatsapp.MIME_PDF),
                     whatsapp.Documento(b"PK", "Pedido.xlsx", whatsapp.MIME_XLSX)]

    def test_telefono(self):
        self.assertEqual(self.w.normalizar_telefono("987 654 321"), "51987654321")
        self.assertEqual(self.w.normalizar_telefono("+51 987-654-321"), "51987654321")
        self.assertEqual(self.w.normalizar_telefono("0051987654321"), "51987654321")
        self.assertEqual(self.w.normalizar_telefono("123"), "")

    def test_speech_y_variables(self):
        texto = self.w.mensaje_de_avance(self.p, HOY)
        self.assertIn("PED-2026-0012", texto)
        self.assertIn("Arq. Martín Vega", texto)  # le habla al contacto, no a la razón social
        self.assertIn("reproceso", texto)
        variables = self.w.variables_de_plantilla(self.p, HOY)
        self.assertEqual(len(variables), 6)
        self.assertFalse(any("\n" in v or "    " in v for v in variables))

    def test_enlace_wa_me_lleva_el_texto(self):
        enlace = self.w.enlace_wa_me("51987654321", "Hola\nmundo")
        self.assertTrue(enlace.startswith("https://wa.me/51987654321?text=Hola%0Amundo"))

    def test_envio_con_plantilla_pdf_y_excel(self):
        meta = FalsoMeta()
        api = self.w.WhatsAppCloud("TOKEN", "999", abrir=meta)
        res = api.enviar_avance("51987654321", "texto", ["a"] * 6, self.docs)
        self.assertTrue(res.enviado)
        self.assertEqual([p.estado for p in res.pasos], ["ok", "ok"])
        urls = [u.rsplit("/", 1)[1] for u, *_ in meta.peticiones]
        self.assertEqual(urls, ["media", "messages", "media", "messages"])
        import json
        plantilla = json.loads(meta.peticiones[1][2])
        self.assertEqual(plantilla["type"], "template")
        self.assertEqual(plantilla["template"]["components"][0]["parameters"][0]["document"]["filename"], "Pedido.pdf")
        self.assertIn(b"multipart", meta.peticiones[0][1].encode())
        self.assertEqual(meta.peticiones[0][3], "Bearer TOKEN")

    def test_excel_fuera_de_ventana_es_aviso_no_fallo(self):
        api = self.w.WhatsAppCloud("T", "999", abrir=FalsoMeta(fallar_documentos_con=131047))
        res = api.enviar_avance("51987654321", "texto", ["a"] * 6, self.docs)
        self.assertTrue(res.enviado)
        self.assertEqual(res.pasos[-1].estado, "aviso")
        self.assertIn("24 h", res.pasos[-1].detalle)

    def test_sin_plantilla_va_texto_libre_y_dos_archivos(self):
        import json
        meta = FalsoMeta()
        api = self.w.WhatsAppCloud("T", "999", plantilla="", abrir=meta)
        res = api.enviar_avance("51987654321", "Hola", ["a"] * 6, self.docs)
        tipos = [json.loads(c)["type"] for u, _, c, _ in meta.peticiones if u.endswith("messages")]
        self.assertEqual(tipos, ["text", "document", "document"])
        self.assertTrue(all("id wamid.1" in p.detalle for p in res.pasos))

    def test_sin_numero_no_envia(self):
        meta = FalsoMeta()
        res = self.w.WhatsAppCloud("T", "999", abrir=meta).enviar_avance("", "x", [], self.docs)
        self.assertFalse(res.enviado)
        self.assertEqual(meta.peticiones, [])

    def test_sin_secrets_no_hay_api(self):
        self.assertIsNone(self.w.WhatsAppCloud.desde_config({}))


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
        self.assertIn("Datos de demostración", texto)

    def test_vista_de_cliente_solo_ve_lo_suyo(self):
        at = self.correr(vista="Minera Los Andes S.A.C. (demo)")
        texto = self.html(at)
        self.assertIn("Minera Los Andes", texto)
        self.assertNotIn("Pesquera Mar Azul", texto)
        self.assertNotIn("nav_Conexión de datos", [b.key for b in at.button])

    def test_detalle(self):
        at = self.correr(pedido="PED-2026-0012")
        texto = self.html(at)
        self.assertIn("Registro de la trazabilidad", texto)
        self.assertIn("ISO 8.7", texto)

    def test_cliente_no_abre_pedidos_ajenos(self):
        at = self.correr(vista="Minera Los Andes S.A.C. (demo)", pedido="PED-2026-0012")
        self.assertNotIn("Constructora Pacífico", self.html(at))

    def test_el_menu_no_usa_radios_y_lleva_el_logo(self):
        at = self.correr()
        self.assertFalse(at.radio)
        self.assertIn("logo-caja", self.html(at))
        activos = [b.key for b in at.button if b.key.startswith("nav_") and b.proto.type == "primary"]
        self.assertEqual(activos, ["nav_Tablero"])

    def test_descargas_y_selector(self):
        at = self.correr()
        self.assertEqual(at.selectbox[0].label, "Cliente")
        self.assertTrue(at.selectbox[0].options[0].startswith("Todos los clientes"))
        self.assertIn("Agroindustrias Valle Verde", at.selectbox[0].options)
        at.segmented_control[0].set_value("Todo el historial").run()
        self.assertIn("ISO 9.1.2 · historial", self.html(at))
        at = self.correr(pedido="PED-2026-0012")
        self.assertTrue(any(b.key == "descarga_proforma" for b in at.get("download_button")))

    def test_boton_whatsapp_abre_el_dialogo_demo(self):
        at = self.correr(pedido="PED-2026-0012")
        at.button(key="wsp_pedido").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(at.error, [e.value for e in at.error])
        self.assertEqual(at.segmented_control[-1].value, "Mi número (prueba)")  # primero, a uno mismo
        self.assertIn("wa.me", " ".join(str(b.proto) for b in at.get("link_button")))
        at = self.correr(vista="Minera Los Andes S.A.C. (demo)")
        at.button(key="wsp_cliente").click().run()
        self.assertFalse(at.exception, at.exception)

    def test_lista_y_conexion(self):
        at = self.correr()
        for pagina in ("Lista de pedidos", "Conexión de datos"):
            at.button(key=f"nav_{pagina}").click().run()
            self.assertFalse(at.exception, at.exception)
            self.assertFalse(at.error, [e.value for e in at.error])


if __name__ == "__main__":
    unittest.main(verbosity=1)
