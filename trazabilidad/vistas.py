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
    clase = f"tarjeta tono-{tono}" + (" activa" if p.codigo == seleccionado else "")
    return (
        f'<a class="{clase}" href="{esc(enlace(pedido=p.codigo, vista=vista))}" target="_self">'
        f'<div class="codigo">{esc(p.codigo)}</div>'
        f'<div class="cliente">{esc(p.cliente)}</div>'
        f'<div class="productos">{esc(p.resumen)}</div>'
        f'{barra}'
        f'<div class="pie"><span class="chip {tono}">{esc(texto)}</span>'
        f'<span class="entrega">{fecha_corta(entrega)}</span></div>'
        f'</a>'
    )


def referencia_columna(clave: str, referencia: str, dias_entregado: int | None) -> str:
    if clave != "entregado":
        return referencia
    return f"{referencia} · {dias_entregado} días" if dias_entregado else f"{referencia} · historial"


def tablero(pedidos: list[Pedido], hoy: date, vista: str, seleccionado: str = "",
            dias_produccion: int = 15, dias_entregado: int | None = 30) -> str:
    grupos = por_etapa(pedidos, hoy, dias_entregado)
    columnas, accesos = [], []
    for etapa in ETAPAS:
        lista = grupos[etapa.clave]
        cuerpo = "".join(tarjeta(p, hoy, vista, seleccionado, dias_produccion) for p in lista)
        if not cuerpo:
            cuerpo = '<div class="vacio">Sin pedidos en esta etapa</div>'
        accesos.append(f'<a href="#col-{etapa.clave}">{esc(etapa.nombre)} <b>{len(lista)}</b></a>')
        columnas.append(
            f'<section class="columna" id="col-{etapa.clave}">'
            f'<header><h3>{esc(etapa.nombre)}</h3><span class="conteo">{len(lista)}</span></header>'
            f'<div class="norma" title="{esc(etapa.descripcion)}">'
            f'{esc(referencia_columna(etapa.clave, etapa.referencia, dias_entregado))}</div>'
            f'<div class="tarjetas">{cuerpo}</div>'
            f'</section>'
        )
    return (
        '<div class="tablero-cab"><b>Pedidos por etapa</b>'
        '<span>Cada etapa deja su registro ISO automáticamente</span></div>'
        f'<nav class="etapas-nav">{"".join(accesos)}</nav>'
        f'<div class="tablero">{"".join(columnas)}</div>'
    )


ICONOS = {
    "caja": '<path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    "alerta": '<path d="M12 9v4m0 4h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
    "escudo": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    "reloj": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "estrella": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9L12 3Z"/>',
}


def indicador(titulo: str, valor: str, nota: str = "", tono: str = "", icono: str = "caja") -> str:
    svg = (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
           f'stroke-linecap="round" stroke-linejoin="round">{ICONOS[icono]}</svg>')
    return (f'<div class="kpi {tono}"><div class="kpi-ico">{svg}</div><div>'
            f'<div class="kpi-t">{esc(titulo)}</div><div class="kpi-v">{esc(valor)}</div>'
            f'<div class="kpi-n">{esc(nota)}</div></div></div>')


def fila_indicadores(ind: dict) -> str:
    a_tiempo = "—" if ind["a_tiempo"] is None else f"{ind['a_tiempo']:.0%}"
    satis = "—" if ind["satisfaccion"] is None else f"{ind['satisfaccion']:.1f} / 5"
    prendas = f"{ind['prendas_en_curso']:,}".replace(",", ".")
    return '<div class="kpis">' + "".join([
        indicador("Pedidos en curso", str(ind["activos"]), f"{prendas} prendas", icono="caja"),
        indicador("En riesgo o atrasados", str(ind["en_riesgo"]), "requieren atención",
                  "alerta" if ind["en_riesgo"] else "bien", "alerta"),
        indicador("No conformes abiertos", str(ind["no_conformes"]), "ISO 8.7",
                  "aviso" if ind["no_conformes"] else "bien", "escudo"),
        indicador("Entregas a tiempo", a_tiempo,
                  f"{ind['entregados']} entregados" if ind["entregados"] else "aún sin entregas", icono="reloj"),
        indicador("Satisfacción", satis,
                  "Encuesta ISO 9.1.2" if ind["satisfaccion"] is not None else "aún sin encuestas", icono="estrella"),
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
    return f'<div class="stepper caja">{"".join(pasos)}</div>'


def subetapas(p: Pedido) -> str:
    if p.etapa != "produccion":
        return ""
    actual = SUBETAPAS_PRODUCCION.index(p.subetapa)
    items = []
    for i, nombre in enumerate(SUBETAPAS_PRODUCCION):
        estado = "hecho" if i < actual else ("actual" if i == actual else "pendiente")
        items.append(f'<span class="sub {estado}">{esc(nombre)}</span>')
    return (f'<div class="subetapas caja"><div class="sub-t">Producción · {p.avance_produccion:.0%}</div>'
            f'{"".join(items)}</div>')


def cabecera_pedido(p: Pedido, hoy: date, dias_produccion: int = 15) -> str:
    texto, tono = etiqueta(p, hoy, dias_produccion)
    avance = avance_general(p)
    return (
        '<div class="detalle-cab caja">'
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
    return f'<ul class="timeline caja">{"".join(filas)}</ul>'


def boton_compartir(texto: str, documentos: list, enlace_wa: str) -> str:
    """Botón que comparte el mensaje con el PDF y el Excel adjuntos, SIN la API de WhatsApp.

    Usa el menú "Compartir" del sistema (Web Share API): en el celular se elige
    WhatsApp y el contacto, y llegan el texto y los dos archivos. No necesita token.

    Va dentro del iframe de Streamlit, que no tiene permiso `web-share`; por eso
    se llama al `navigator.share` de la página principal (mismo origen) y el del
    iframe queda de respaldo. Donde el navegador no comparte archivos (algunos
    computadores), se descargan los archivos y se abre WhatsApp con el texto.
    """
    import base64
    import json

    datos = {
        "texto": texto,
        "wa": enlace_wa,
        "docs": [{"nombre": d.nombre, "mime": d.mime, "b64": base64.b64encode(d.contenido).decode()}
                 for d in documentos],
    }
    # "</" cerraría el <script> antes de tiempo: se escapa.
    carga = json.dumps(datos).replace("</", "<\\/")
    return """<!doctype html><html><head><meta charset="utf-8">
<style>
 body{margin:0;font-family:Inter,system-ui,-apple-system,sans-serif}
 button{width:100%;min-height:46px;border:0;border-radius:10px;background:#1FA855;color:#fff;
        font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px}
 button:hover{background:#178A45}
 .sub{font-size:12px;color:#667085;text-align:center;margin-top:5px}
 .estado{font-size:12.5px;color:#475467;margin-top:7px;line-height:1.4;min-height:16px}
</style></head><body>
<button id="b" type="button">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>
  <path d="m16 6-4-4-4 4"/><path d="M12 2v13"/></svg>
 Compartir por WhatsApp</button>
<div class="sub">Mensaje + PDF + Excel · elige WhatsApp y el chat</div>
<div class="estado" id="e"></div>
<script>
const DATOS = """ + carga + """;
const estado = t => document.getElementById("e").textContent = t;
function archivo(d) {
  const bin = atob(d.b64), u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return new File([u], d.nombre, {type: d.mime});
}
async function compartir() {
  const files = DATOS.docs.map(archivo);
  const paquete = {text: DATOS.texto, files: files};
  const navegadores = [];
  try { navegadores.push(window.parent.navigator); } catch (e) {}
  navegadores.push(navigator);
  for (const n of navegadores) {
    try {
      if (n.canShare && n.canShare(paquete)) {
        await n.share(paquete);
        estado("Listo. Revisa tu WhatsApp: deben estar el mensaje y los dos archivos.");
        return;
      }
    } catch (err) {
      if (err && err.name === "AbortError") { estado("Cancelado."); return; }
    }
  }
  for (const f of files) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(f); a.download = f.name;
    document.body.appendChild(a); a.click(); a.remove();
  }
  window.open(DATOS.wa, "_blank");
  estado("Este navegador no deja compartir archivos: se descargaron y se abrió WhatsApp con el texto. " +
         "Adjúntalos desde Descargas. En el celular el botón comparte todo junto.");
}
document.getElementById("b").addEventListener("click", compartir);
</script></body></html>"""


# --- Costos ----------------------------------------------------------------------

COLORES_ELEMENTO = {  # categórica validada (scripts/validate_palette.js): orden fijo, nunca se recicla
    "Materia prima": "#2a78d6", "Mano de obra": "#eb6834", "Terceros": "#1baf7a", "Indirectos (CIF)": "#eda100",
}


def soles(n) -> str:
    return "—" if n is None else f"S/ {n:,.0f}" if abs(n) >= 1000 else f"S/ {n:,.2f}"


def estructura_del_costo(elementos: dict[str, float]) -> str:
    """Parte de un todo: una barra al 100 % con etiqueta directa y leyenda (nunca solo color)."""
    total = sum(elementos.values()) or 1
    segmentos, leyenda = [], []
    for nombre, valor in elementos.items():
        pct = valor / total
        color = COLORES_ELEMENTO.get(nombre, "#909090")
        etiqueta = f"{pct:.0%}" if pct >= 0.07 else ""
        segmentos.append(f'<div class="seg" style="width:{pct * 100:.2f}%;background:{color}" '
                         f'title="{esc(nombre)}: {esc(soles(valor))} ({pct:.1%})"><span>{etiqueta}</span></div>')
        leyenda.append(f'<div class="ley"><i style="background:{color}"></i><span>{esc(nombre)}</span>'
                       f'<b>{esc(soles(valor))}</b><small>{pct:.1%}</small></div>')
    return (f'<div class="caja grafico"><div class="graf-t">Estructura del costo</div>'
            f'<div class="graf-s">De cada sol que cuesta producir, cuánto va a cada elemento</div>'
            f'<div class="apilada">{"".join(segmentos)}</div><div class="leyenda">{"".join(leyenda)}</div></div>')


def barras_por_centro(filas: list[tuple[str, float]], titulo: str, subtitulo: str) -> str:
    """Magnitud por categoría: barras horizontales de un solo color, valor al final de cada barra."""
    maximo = max((v for _, v in filas), default=0) or 1
    cuerpo = "".join(
        f'<div class="hb-fila" title="{esc(n)}: {esc(soles(v))}"><span class="hb-n">{esc(n)}</span>'
        f'<div class="hb-pista"><div class="hb-barra" style="width:{v / maximo * 100:.2f}%"></div></div>'
        f'<span class="hb-v">{esc(soles(v))}</span></div>' for n, v in filas)
    return (f'<div class="caja grafico"><div class="graf-t">{esc(titulo)}</div>'
            f'<div class="graf-s">{esc(subtitulo)}</div>{cuerpo}</div>')


def fila_indicadores_costos(k: dict, periodo: str) -> str:
    margen = k["margen_pct"]
    return '<div class="kpis">' + "".join([
        indicador("Costo de producción", soles(k["costo_total"]), f"{k['ots']} OT · {periodo}", icono="caja"),
        indicador("Costo unitario promedio", soles(k["costo_unitario"]), f"{k['unidades']:,.0f} prendas", icono="reloj"),
        indicador("Margen bruto", "—" if margen is None else f"{margen:.1%}",
                  "OT terminadas, sin IGV" if margen is not None else "elige «Todo el historial»",
                  "alerta" if (margen is not None and margen < 0.15) else "", "estrella"),
        indicador("Costo de no calidad", soles(k["no_calidad"]), "merma + arreglos",
                  "aviso" if k["no_calidad"] else "bien", "escudo"),
        indicador("OT bajo margen mínimo", str(k["ots_margen_bajo"]), "margen menor a 15 %",
                  "alerta" if k["ots_margen_bajo"] else "bien", "alerta"),
    ]) + "</div>"
