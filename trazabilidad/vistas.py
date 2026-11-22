"""HTML del tablero y del detalle. Funciones puras: reciben pedidos, devuelven texto.

Todo texto que viene de la fuente de datos pasa por `esc()`: un nombre de
cliente con `<` o `&` no puede romper la pantalla ni inyectar marcado.
"""

from __future__ import annotations

from datetime import date
from html import escape
from urllib.parse import urlencode

from trazabilidad.modelo import (ETAPAS, ETAPAS_POR_CLAVE, ORDEN_ETAPA, SUBETAPAS_PRODUCCION,
                                 Pedido, avance_general, etiqueta, por_etapa)

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def esc(valor: object) -> str:
    return escape(str(valor or ""), quote=True)


def fecha_corta(d: date | None) -> str:
    return "—" if d is None else f"{d.day:02d} {MESES[d.month - 1]} {d.year}"


def enlace(**params: str) -> str:
    return "?" + urlencode({k: v for k, v in params.items() if v})


def tarjeta(p: Pedido, hoy: date, vista: str, seleccionado: str = "", dias_produccion: int = 15) -> str:
    texto, tono = etiqueta(p, hoy, dias_produccion)
    barra = ""
    if p.etapa == "produccion":
        barra = (f'<div class="barra" title="Avance {p.avance_produccion:.0%}">'
                 f'<span style="width:{p.avance_produccion * 100:.0f}%"></span></div>')
    entrega = p.fecha_entregado if p.entregado and p.fecha_entregado else p.fecha_entrega
    clase = "tarjeta activa" if p.codigo == seleccionado else "tarjeta"
    return (
        f'<a class="{clase}" href="{esc(enlace(pedido=p.codigo, vista=vista))}" target="_self">'
        f'<div class="codigo">{esc(p.codigo)}</div>'
        f'<div class="cliente">{esc(p.cliente)}</div>'
        f'<div class="productos">{esc(p.resumen)}</div>'
        f'{barra}'
        f'<div class="chip {tono}">{esc(texto)}</div>'
        f'<div class="entrega">Entrega {fecha_corta(entrega)}</div>'
        f'</a>'
    )


def tablero(pedidos: list[Pedido], hoy: date, vista: str, seleccionado: str = "",
            dias_produccion: int = 15) -> str:
    grupos = por_etapa(pedidos, hoy)
    columnas = []
    for etapa in ETAPAS:
        lista = grupos[etapa.clave]
        cuerpo = "".join(tarjeta(p, hoy, vista, seleccionado, dias_produccion) for p in lista)
        if not cuerpo:
            cuerpo = '<div class="vacio">Sin pedidos en esta etapa</div>'
        columnas.append(
            f'<section class="columna">'
            f'<header><h3>{esc(etapa.nombre)}</h3><span class="conteo">{len(lista)}</span></header>'
            f'<div class="norma" title="{esc(etapa.descripcion)}">{esc(etapa.referencia)}</div>'
            f'<div class="tarjetas">{cuerpo}</div>'
            f'</section>'
        )
    return (
        '<div class="tablero-cab">Cada etapa deja su registro ISO automáticamente</div>'
        f'<div class="tablero">{"".join(columnas)}</div>'
    )


def indicador(titulo: str, valor: str, nota: str = "", tono: str = "") -> str:
    return (f'<div class="kpi {tono}"><div class="kpi-t">{esc(titulo)}</div>'
            f'<div class="kpi-v">{esc(valor)}</div><div class="kpi-n">{esc(nota)}</div></div>')


def fila_indicadores(ind: dict) -> str:
    a_tiempo = "—" if ind["a_tiempo"] is None else f"{ind['a_tiempo']:.0%}"
    satis = "—" if ind["satisfaccion"] is None else f"{ind['satisfaccion']:.1f} / 5"
    prendas = f"{ind['prendas_en_curso']:,}".replace(",", ".")
    return '<div class="kpis">' + "".join([
        indicador("Pedidos en curso", str(ind["activos"]), f"{prendas} prendas"),
        indicador("En riesgo o atrasados", str(ind["en_riesgo"]), "requieren atención",
                  "alerta" if ind["en_riesgo"] else ""),
        indicador("No conformes abiertos", str(ind["no_conformes"]), "ISO 8.7",
                  "aviso" if ind["no_conformes"] else ""),
        indicador("Entregas a tiempo", a_tiempo, f"{ind['entregados']} entregados"),
        indicador("Satisfacción", satis, "ISO 9.1.2"),
    ]) + "</div>"


def stepper(p: Pedido) -> str:
    actual = ORDEN_ETAPA.get(p.etapa, 0)
    pasos = []
    for i, etapa in enumerate(ETAPAS):
        if i < actual or p.entregado:
            estado, marca = "hecho", "✓"
        elif i == actual:
            estado, marca = "actual", str(i + 1)
        else:
            estado, marca = "pendiente", str(i + 1)
        pasos.append(f'<div class="paso {estado}"><div class="bola">{marca}</div>'
                     f'<div class="paso-n">{esc(etapa.nombre)}</div>'
                     f'<div class="paso-r">{esc(etapa.referencia)}</div></div>')
    return f'<div class="stepper">{"".join(pasos)}</div>'


def subetapas(p: Pedido) -> str:
    if p.etapa != "produccion":
        return ""
    actual = SUBETAPAS_PRODUCCION.index(p.subetapa)
    items = []
    for i, nombre in enumerate(SUBETAPAS_PRODUCCION):
        estado = "hecho" if i < actual else ("actual" if i == actual else "pendiente")
        items.append(f'<span class="sub {estado}">{esc(nombre)}</span>')
    return (f'<div class="subetapas"><div class="sub-t">Producción · {p.avance_produccion:.0%}</div>'
            f'{"".join(items)}</div>')


def cabecera_pedido(p: Pedido, hoy: date, dias_produccion: int = 15) -> str:
    texto, tono = etiqueta(p, hoy, dias_produccion)
    avance = avance_general(p)
    return (
        '<div class="detalle-cab">'
        f'<div><div class="codigo">{esc(p.codigo)}</div>'
        f'<h2>{esc(p.cliente)}</h2>'
        f'<div class="productos">{esc(p.resumen)} prendas</div></div>'
        '<div class="detalle-datos">'
        f'<div><span>Pedido</span><b>{fecha_corta(p.fecha_pedido)}</b></div>'
        f'<div><span>Entrega comprometida</span><b>{fecha_corta(p.fecha_entrega)}</b></div>'
        f'<div><span>Etapa</span><b>{esc(ETAPAS_POR_CLAVE[p.etapa].nombre)}</b></div>'
        f'<div><span>Estado</span><b class="chip {tono}">{esc(texto)}</b></div>'
        '</div>'
        f'<div class="barra grande" title="Avance general {avance:.0%}">'
        f'<span style="width:{avance * 100:.0f}%"></span></div>'
        f'<div class="avance-t">Avance general {avance:.0%}</div>'
        '</div>'
    )


def linea_de_tiempo(p: Pedido) -> str:
    if not p.eventos:
        return '<div class="vacio">Este pedido todavía no tiene registros.</div>'
    filas = []
    for e in reversed(p.eventos):
        evidencia = f'<span class="evidencia">📎 {esc(e.evidencia)}</span>' if e.evidencia else ""
        filas.append(
            '<li>'
            f'<div class="t-fecha">{fecha_corta(e.fecha.date())} · {e.fecha:%H:%M}</div>'
            f'<div class="t-cuerpo"><span class="norma">{esc(e.clausula or "Registro")}</span>'
            f'<div class="t-desc">{esc(e.descripcion)}</div>'
            f'<div class="t-pie">{esc(e.responsable)} {evidencia}</div></div>'
            '</li>'
        )
    return f'<ul class="timeline">{"".join(filas)}</ul>'
