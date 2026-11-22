"""Descargas: proforma de un pedido (PDF), resumen de pedidos (PDF) y Excel.

Sin Streamlit: reciben pedidos y devuelven bytes. Las reglas de estado salen
de `modelo` (la misma `etiqueta` del tablero), así que el PDF dice lo mismo que
la pantalla.

Las fuentes base de PDF solo entienden latin-1: `t()` cambia los pocos signos
que no caben (— … → “ ”) por su equivalente, en vez de dejar un "?" o reventar.
"""

from __future__ import annotations

import io
from datetime import date, datetime, time
from pathlib import Path

from fpdf import FPDF, FontFace
from fpdf.enums import TableCellFillMode

from trazabilidad.modelo import ETAPAS_POR_CLAVE, Pedido, avance_general, etiqueta, indicadores

LOGO = Path(__file__).resolve().parents[1] / "assets" / "logo_contex.png"
IGV = 0.18

MARINO = (18, 56, 107)
ACCION = (31, 95, 175)
GRIS = (102, 112, 133)
TEXTO = (20, 33, 61)
FONDO = (243, 245, 249)
BORDE = (223, 229, 238)
TONOS = {  # (fondo, texto) de cada etiqueta, iguales a la pantalla
    "rojo": ((253, 232, 231), (180, 35, 24)),
    "ambar": ((254, 243, 214), (147, 89, 10)),
    "azul": ((227, 237, 251), (31, 95, 175)),
    "verde": ((227, 244, 232), (29, 122, 62)),
    "gris": ((238, 241, 245), (75, 85, 101)),
}
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")
_CAMBIOS = {"—": "-", "–": "-", "−": "-", "≥": ">=", "≤": "<=", "…": "...", "→": "->", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "-"}


def t(texto: object) -> str:
    s = str(texto if texto is not None else "")
    for a, b in _CAMBIOS.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def soles(n: float | None) -> str:
    return "-" if n is None else f"S/ {n:,.2f}"


def fecha_larga(d: date | None) -> str:
    return "-" if d is None else f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(d: date | None) -> str:
    return "-" if d is None else f"{d:%d/%m/%Y}"


class Documento(FPDF):
    def __init__(self, titulo: str, subtitulo: str, orientacion: str = "P", demo: bool = False):
        super().__init__(orientation=orientacion, unit="mm", format="A4")
        self.titulo, self.subtitulo, self.demo = titulo, subtitulo, demo
        self.set_auto_page_break(True, margin=18)
        self.set_margins(14, 14, 14)
        self.alias_nb_pages()

    def header(self):
        ancho = self.w
        self.set_fill_color(*MARINO)
        self.rect(0, 0, ancho, 30, "F")
        self.set_fill_color(255, 255, 255)
        self.rect(14, 5, 22, 22, "F")
        if LOGO.exists():
            self.image(str(LOGO), x=16.5, y=6, h=20)
        self.set_text_color(255, 255, 255)
        self.set_xy(40, 8)
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 7, t(self.titulo))
        self.set_xy(40, 16)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(201, 212, 229)
        self.cell(0, 5, t(self.subtitulo))
        self.set_xy(ancho - 84, 9)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(255, 255, 255)
        self.cell(70, 5, "CONTEX FYG", align="R")
        self.set_xy(ancho - 84, 15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(201, 212, 229)
        self.cell(70, 5, t("Trazabilidad de pedidos · ISO 9001"), align="R")
        if self.demo:
            self.set_xy(ancho - 84, 21)
            self.set_text_color(245, 181, 71)
            self.set_font("Helvetica", "B", 7.5)
            self.cell(70, 4, t("DATOS DE DEMOSTRACIÓN"), align="R")
        self.set_y(38)
        self.set_text_color(*TEXTO)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*BORDE)
        self.line(14, self.get_y() - 1, self.w - 14, self.get_y() - 1)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*GRIS)
        self.cell(0, 5, t(f"Generado el {fecha_larga(date.today())} · Contex FYG · Trazabilidad de pedidos"))
        self.cell(0, 5, f"{self.page_no()} / {{nb}}", align="R")

    # --- piezas --------------------------------------------------------------
    def rotulo(self, texto: str):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 5, t(texto.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*TEXTO)

    def seccion(self, texto: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*MARINO)
        self.cell(0, 7, t(texto), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*MARINO)
        self.set_line_width(.5)
        self.line(self.l_margin, self.get_y(), self.l_margin + 18, self.get_y())
        self.set_line_width(.2)
        self.ln(3)
        self.set_text_color(*TEXTO)

    def chip(self, texto: str, tono: str, x: float, y: float):
        fondo, color = TONOS.get(tono, TONOS["gris"])
        self.set_font("Helvetica", "B", 8)
        ancho = self.get_string_width(t(texto)) + 6
        self.set_fill_color(*fondo)
        self.set_text_color(*color)
        self.set_xy(x, y)
        self.cell(ancho, 5.5, t(texto), align="C", fill=True)
        self.set_text_color(*TEXTO)

    def barra(self, avance: float, x: float, y: float, ancho: float):
        self.set_fill_color(*BORDE)
        self.rect(x, y, ancho, 2.4, "F")
        self.set_fill_color(*MARINO)
        self.rect(x, y, max(ancho * avance, .1), 2.4, "F")

    def tarjeta_dato(self, x, y, w, titulo, valor, nota=""):
        self.set_fill_color(*FONDO)
        self.rect(x, y, w, 19, "F")
        self.set_xy(x + 4, y + 2.5)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*GRIS)
        self.cell(w - 8, 4, t(titulo))
        self.set_xy(x + 4, y + 7)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*TEXTO)
        self.cell(w - 8, 6, t(valor))
        if nota:
            self.set_xy(x + 4, y + 13.5)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*GRIS)
            self.cell(w - 8, 4, t(nota))
        self.set_text_color(*TEXTO)

    def tabla(self, cabecera, filas, anchos, alineacion):
        self.set_font("Helvetica", "", 8.5)
        self.set_draw_color(*BORDE)
        with self.table(col_widths=anchos, text_align=alineacion, line_height=6.2,
                        headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=MARINO),
                        cell_fill_mode=TableCellFillMode.NONE,
                        borders_layout="HORIZONTAL_LINES", padding=1.6) as tabla:
            fila = tabla.row()
            for c in cabecera:
                fila.cell(t(c))
            par = FontFace(fill_color=FONDO, color=TEXTO)
            impar = FontFace(fill_color=(255, 255, 255), color=TEXTO)
            for i, datos in enumerate(filas):
                fila = tabla.row(style=par if i % 2 else impar)
                for c in datos:
                    fila.cell(t(c))


# --- Proforma de un pedido ----------------------------------------------------

def pdf_pedido(p: Pedido, hoy: date, demo: bool = False, dias_produccion: int = 15) -> bytes:
    titulo = "PROFORMA Y ESTADO DEL PEDIDO" if p.con_precios else "ESTADO DEL PEDIDO"
    doc = Documento(titulo, f"Pedido {p.codigo}", demo=demo)
    doc.add_page()

    # Cliente y datos del pedido
    y = doc.get_y()
    doc.set_xy(14, y)
    doc.rotulo("Cliente")
    doc.set_font("Helvetica", "B", 13)
    doc.multi_cell(105, 6, t(p.cliente), new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Helvetica", "", 9)
    doc.set_text_color(*GRIS)
    doc.cell(105, 5, t(f"{p.cantidad_total:,} prendas · {len(p.lineas)} producto(s)"))
    datos = [("N.º de pedido", p.codigo), ("Fecha del pedido", fecha_corta(p.fecha_pedido)),
             ("Entrega comprometida", fecha_corta(p.fecha_entrega)), ("Emitido", fecha_corta(hoy))]
    doc.set_xy(128, y)
    for k, v in datos:
        doc.set_x(128)
        doc.set_font("Helvetica", "", 8)
        doc.set_text_color(*GRIS)
        doc.cell(34, 5.5, t(k))
        doc.set_font("Helvetica", "B", 9)
        doc.set_text_color(*TEXTO)
        doc.cell(34, 5.5, t(v), align="R", new_x="LMARGIN", new_y="NEXT")
    doc.set_y(max(doc.get_y(), y + 26))

    # Detalle de productos
    doc.seccion("Detalle de productos")
    if p.con_precios:
        filas = [(str(i), l.producto, f"{l.cantidad:,}", soles(l.precio_unitario), soles(l.importe))
                 for i, l in enumerate(p.lineas, 1)]
        doc.tabla(("#", "Producto", "Cantidad", "Precio unit.", "Importe"), filas,
                  (8, 92, 24, 29, 29), ("C", "LEFT", "RIGHT", "RIGHT", "RIGHT"))
        igv = p.subtotal * IGV
        doc.ln(2)
        for etiqueta_total, valor, negrita in (("Subtotal", p.subtotal, False),
                                                ("IGV (18 %)", igv, False),
                                                ("Total", p.subtotal + igv, True)):
            doc.set_x(124)
            if negrita:
                doc.set_fill_color(*MARINO)
                doc.set_text_color(255, 255, 255)
            doc.set_font("Helvetica", "B" if negrita else "", 10 if negrita else 9)
            doc.cell(36, 7, t(etiqueta_total), fill=negrita)
            doc.cell(36, 7, soles(valor), align="R", fill=negrita, new_x="LMARGIN", new_y="NEXT")
            doc.set_text_color(*TEXTO)
    else:
        doc.tabla(("#", "Producto", "Cantidad"),
                  [(str(i), l.producto, f"{l.cantidad:,}") for i, l in enumerate(p.lineas, 1)],
                  (10, 142, 30), ("C", "LEFT", "RIGHT"))

    # Estado de la trazabilidad
    doc.seccion("Estado de la trazabilidad")
    texto, tono = etiqueta(p, hoy, dias_produccion)
    avance = avance_general(p)
    y = doc.get_y()
    doc.set_font("Helvetica", "", 8)
    doc.set_text_color(*GRIS)
    doc.cell(30, 5, "Etapa actual")
    doc.set_font("Helvetica", "B", 10)
    doc.set_text_color(*TEXTO)
    etapa = ETAPAS_POR_CLAVE[p.etapa]
    doc.cell(70, 5, t(f"{etapa.nombre}  ({etapa.referencia})"))
    doc.chip(texto, tono, 128, y - .3)
    doc.set_xy(14, y + 8)
    doc.barra(avance, 14, y + 8, 182)
    doc.set_xy(14, y + 11.5)
    doc.set_font("Helvetica", "", 8)
    doc.set_text_color(*GRIS)
    doc.cell(0, 5, t(f"Avance general {avance:.0%}"), new_x="LMARGIN", new_y="NEXT")
    doc.ln(2)

    if p.eventos:
        filas = [(f"{e.fecha:%d/%m/%Y %H:%M}", e.clausula or "-", e.descripcion, e.responsable or "-")
                 for e in reversed(p.eventos)]
        doc.tabla(("Fecha", "Referencia", "Registro", "Responsable"), filas,
                  (28, 26, 84, 44), ("LEFT", "LEFT", "LEFT", "LEFT"))

    if p.con_precios:
        doc.ln(5)
        doc.set_font("Helvetica", "", 7.5)
        doc.set_text_color(*GRIS)
        doc.multi_cell(0, 4, t("Precios en soles. Proforma válida por 15 días desde su emisión. "
                               "Los plazos se cuentan desde la aprobación de la ficha técnica y el pago "
                               "del adelanto. El estado del pedido corresponde a la fecha de emisión."))
    return bytes(doc.output())


# --- Resumen de varios pedidos ------------------------------------------------

def pdf_resumen(pedidos: list[Pedido], hoy: date, alcance: str, demo: bool = False,
                dias_produccion: int = 15) -> bytes:
    doc = Documento("RESUMEN DE PEDIDOS", t(f"{alcance} · al {fecha_larga(hoy)}"), "L", demo)
    doc.add_page()
    ind = indicadores(pedidos, hoy, dias_produccion)
    total = sum(p.subtotal for p in pedidos if p.con_precios)
    tarjetas = [
        ("Pedidos", str(len(pedidos)), f"{ind['activos']} en curso · {ind['entregados']} entregados"),
        ("Prendas en curso", f"{ind['prendas_en_curso']:,}", ""),
        ("En riesgo o atrasados", str(ind["en_riesgo"]), "requieren atención"),
        ("Entregas a tiempo", "-" if ind["a_tiempo"] is None else f"{ind['a_tiempo']:.0%}", ""),
        ("Satisfacción", "-" if ind["satisfaccion"] is None else f"{ind['satisfaccion']:.1f} / 5", "ISO 9.1.2"),
        ("Valor de los pedidos", soles(total) if total else "-", "sin IGV"),
    ]
    ancho = (doc.w - 28 - 5 * 4) / 6
    y = doc.get_y()
    for i, (a, b, c) in enumerate(tarjetas):
        doc.tarjeta_dato(14 + i * (ancho + 4), y, ancho, a, b, c)
    doc.set_y(y + 25)

    doc.seccion("Pedidos")
    orden = sorted(pedidos, key=lambda p: (p.entregado, p.fecha_entrega))
    filas = []
    for p in orden:
        texto, _ = etiqueta(p, hoy, dias_produccion)
        filas.append((p.codigo, p.cliente, p.productos, f"{p.cantidad_total:,}",
                      ETAPAS_POR_CLAVE[p.etapa].nombre, texto, f"{avance_general(p):.0%}",
                      fecha_corta(p.fecha_entrega), soles(p.subtotal) if p.con_precios else "-"))
    doc.tabla(("Pedido", "Cliente", "Productos", "Prendas", "Etapa", "Estado", "Avance", "Entrega", "Importe"),
              filas, (27, 48, 66, 16, 26, 30, 14, 20, 22),
              ("LEFT", "LEFT", "LEFT", "RIGHT", "LEFT", "LEFT", "RIGHT", "LEFT", "RIGHT"))
    return bytes(doc.output())


# --- Excel ---------------------------------------------------------------------

def excel_resumen(pedidos: list[Pedido], hoy: date, alcance: str, dias_produccion: int = 15) -> bytes:
    import xlsxwriter

    salida = io.BytesIO()
    libro = xlsxwriter.Workbook(salida, {"in_memory": True, "strings_to_formulas": False,
                                         "strings_to_urls": False})
    f = {
        "titulo": libro.add_format({"bold": True, "font_size": 16, "font_color": "#12386B"}),
        "sub": libro.add_format({"font_color": "#667085"}),
        "cab": libro.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#12386B",
                                 "border": 1, "border_color": "#12386B", "valign": "vcenter"}),
        "txt": libro.add_format({"border": 1, "border_color": "#DFE5EE", "valign": "top", "text_wrap": True}),
        "num": libro.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": "#,##0"}),
        "pct": libro.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": "0%"}),
        "sol": libro.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": '"S/" #,##0.00'}),
        "fec": libro.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": "dd/mm/yyyy", "align": "left"}),
        "fh": libro.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": "dd/mm/yyyy hh:mm", "align": "left"}),
        "kpi_t": libro.add_format({"font_color": "#667085", "bg_color": "#F3F5F9"}),
        "kpi_v": libro.add_format({"bold": True, "font_size": 14, "bg_color": "#F3F5F9", "align": "left"}),
    }

    def hoja(nombre, cabecera, anchos, filas, formatos):
        h = libro.add_worksheet(nombre)
        h.write_row(0, 0, cabecera, f["cab"])
        h.set_row(0, 22)
        for i, a in enumerate(anchos):
            h.set_column(i, i, a)
        for r, fila in enumerate(filas, 1):
            for c, (valor, fmt) in enumerate(zip(fila, formatos)):
                if valor is None or valor == "":
                    h.write_blank(r, c, None, f[fmt])
                elif fmt in ("fec", "fh"):
                    cuando = valor if isinstance(valor, datetime) else datetime.combine(valor, time())
                    h.write_datetime(r, c, cuando, f[fmt])
                else:
                    h.write(r, c, valor, f[fmt])
        h.freeze_panes(1, 0)
        h.autofilter(0, 0, max(len(filas), 1), len(cabecera) - 1)
        return h

    # Resumen
    ind = indicadores(pedidos, hoy, dias_produccion)
    r = libro.add_worksheet("Resumen")
    r.hide_gridlines(2)
    r.set_column(0, 0, 3)
    r.set_column(1, 6, 22)
    if LOGO.exists():
        r.insert_image("B2", str(LOGO), {"x_scale": .28, "y_scale": .28})
    r.write("C2", "Resumen de pedidos", f["titulo"])
    r.write("C3", f"Contex FYG · {alcance} · al {fecha_corta(hoy)}", f["sub"])
    total = sum(p.subtotal for p in pedidos if p.con_precios)
    kpis = [("Pedidos", len(pedidos)), ("En curso", ind["activos"]),
            ("Prendas en curso", ind["prendas_en_curso"]), ("En riesgo o atrasados", ind["en_riesgo"]),
            ("Entregas a tiempo", "-" if ind["a_tiempo"] is None else f"{ind['a_tiempo']:.0%}"),
            ("Satisfacción", "-" if ind["satisfaccion"] is None else f"{ind['satisfaccion']:.1f} / 5"),
            ("Valor (sin IGV)", soles(total) if total else "-")]
    for i, (k, v) in enumerate(kpis):
        fila, col = 6 + (i // 4) * 3, 1 + (i % 4)
        r.write(fila, col, k, f["kpi_t"])
        r.write(fila + 1, col, v, f["kpi_v"])

    filas = []
    for p in sorted(pedidos, key=lambda p: (p.entregado, p.fecha_entrega)):
        texto, _ = etiqueta(p, hoy, dias_produccion)
        filas.append((p.codigo, p.cliente, p.productos, p.cantidad_total, ETAPAS_POR_CLAVE[p.etapa].nombre,
                      texto, avance_general(p), p.fecha_pedido, p.fecha_entrega, p.fecha_entregado,
                      p.subtotal if p.con_precios else None, p.encuesta))
    hoja("Pedidos", ["Pedido", "Cliente", "Productos", "Prendas", "Etapa", "Estado", "Avance",
                     "Fecha pedido", "Entrega", "Entregado", "Importe (sin IGV)", "Encuesta"],
         [16, 34, 46, 10, 18, 24, 9, 13, 13, 13, 17, 10], filas,
         ["txt", "txt", "txt", "num", "txt", "txt", "pct", "fec", "fec", "fec", "sol", "txt"])

    hoja("Productos", ["Pedido", "Cliente", "Producto", "Cantidad", "Precio unit.", "Importe"],
         [16, 34, 40, 11, 13, 15],
         [(p.codigo, p.cliente, l.producto, l.cantidad, l.precio_unitario, l.importe)
          for p in pedidos for l in p.lineas],
         ["txt", "txt", "txt", "num", "sol", "sol"])

    hoja("Registro ISO", ["Pedido", "Cliente", "Fecha", "Etapa", "Referencia", "Registro", "Responsable", "Evidencia"],
         [16, 30, 17, 16, 14, 60, 28, 26],
         [(p.codigo, p.cliente, e.fecha, ETAPAS_POR_CLAVE.get(e.etapa).nombre if e.etapa in ETAPAS_POR_CLAVE else e.etapa,
           e.clausula, e.descripcion, e.responsable, e.evidencia) for p in pedidos for e in p.eventos],
         ["txt", "txt", "fh", "txt", "txt", "txt", "txt", "txt"])

    libro.close()
    return salida.getvalue()
