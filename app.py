"""Contex · Trazabilidad de pedidos.

Tablero para que el cliente vea cómo va su pedido, etapa por etapa, con el
registro ISO que deja cada una. Sin configuración usa datos de demostración;
con la sección [datos] en Secrets lee la base de datos real (ver README).
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from trazabilidad import costos, reportes, vistas, whatsapp
from trazabilidad.conectores import COLUMNAS, ErrorDeDatos, obtener_conector, pedidos_desde_tablas
from trazabilidad.estilos import CSS
from trazabilidad.modelo import (DIAS_PRODUCCION_POR_DEFECTO, ETAPAS_POR_CLAVE, Pedido,
                                 atrasado, en_riesgo, etiqueta, indicadores)

INTERNO = "Todos los clientes"


# --- Datos --------------------------------------------------------------------

def seccion_de_secrets(nombre: str) -> dict:
    """Una sección de Secrets como dict, o {} si no hay Secrets (el caso normal de la demo)."""
    try:
        datos = st.secrets.get(nombre, {})
    except Exception:
        return {}
    return json.loads(json.dumps(datos, default=dict)) if datos else {}


def config_de_datos() -> dict:
    return seccion_de_secrets("datos")


@st.cache_data(ttl=300, show_spinner="Leyendo costos…")
def cargar_costos(config_json: str) -> costos.TablasCosto | None:
    return obtener_conector(json.loads(config_json)).leer_costos()


@st.cache_data(ttl=300, show_spinner="Leyendo pedidos…")
def cargar(config_json: str) -> tuple[list[Pedido], list[str], str, bool]:
    conector = obtener_conector(json.loads(config_json))
    pedidos, avisos = pedidos_desde_tablas(conector.leer_tablas())
    return pedidos, avisos, conector.nombre, conector.es_demo


# --- Navegación ---------------------------------------------------------------

def parametro(nombre: str) -> str:
    valor = st.query_params.get(nombre, "")
    return valor if isinstance(valor, str) else ""


MENU = {
    "Tablero": ":material/view_kanban:",
    "Lista de pedidos": ":material/format_list_bulleted:",
    "Costos": ":material/payments:",
    "Conexión de datos": ":material/database:",
}
LOGO = Path(__file__).parent / "assets" / "logo_contex.png"


@st.cache_data
def logo_base64() -> str:
    return base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""


def ir_a(pagina: str) -> None:
    """on_click del menú: un clic, un rerun."""
    st.session_state["pagina"] = pagina
    st.session_state["cerrar_menu_movil"] = True
    st.query_params.pop("pedido", None)


CERRAR_MENU_MOVIL = """<script>
// En el celular el menú lateral tapa la pantalla: tras elegir una opción se cierra solo.
// En escritorio (más de 640 px) no se toca.
try {
  const p = window.parent;
  if (p.innerWidth <= 640) {
    const b = p.document.querySelector('[data-testid="stSidebarCollapseButton"] button')
           || p.document.querySelector('[data-testid="stSidebarCollapseButton"]');
    const s = p.document.querySelector('[data-testid="stSidebar"]');
    const abierto = s && (s.getAttribute('data-collapsed') === 'false' || s.getAttribute('aria-expanded') === 'true');
    if (b && abierto) b.click();
  }
} catch (e) {}
</script>"""


SUFIJOS = ("S.A.C.", "S.A.A.", "S.A.", "E.I.R.L.", "S.R.L.", "(demo)")


def nombre_corto(cliente: str) -> str:
    """"Agroindustrias Valle Verde S.A. (demo)" -> "Agroindustrias Valle Verde": cabe en el menú."""
    nombre = cliente
    for sufijo in SUFIJOS:
        nombre = nombre.replace(sufijo, "")
    return " ".join(nombre.split()) or cliente


def iniciales(nombre: str) -> str:
    palabras = [w for w in nombre.replace("(demo)", "").split() if w[:1].isalpha()]
    return "".join(w[0] for w in palabras[:2]).upper() or "CX"


def barra_lateral(clientes: dict[str, int], fuente: str, es_demo: bool) -> tuple[str, str]:
    with st.sidebar:
        logo = logo_base64()
        if logo:
            st.markdown(f'<div class="logo-caja"><img src="data:image/png;base64,{logo}" alt="Contex FYG"></div>',
                        unsafe_allow_html=True)
        st.markdown('<div class="app-nombre"><b>Trazabilidad de pedidos</b>'
                    '<span>Seguimiento ISO 9001</span></div>', unsafe_allow_html=True)

        total = sum(clientes.values())
        opciones = [INTERNO] + sorted(clientes)
        pedida = parametro("vista")
        indice = opciones.index(pedida) if pedida in opciones else 0

        def etiqueta_cliente(op: str) -> str:
            return op if op == INTERNO else nombre_corto(op)

        vista = st.selectbox("Cliente", opciones, index=indice, format_func=etiqueta_cliente,
                             help="Cada cliente ve solo sus pedidos. «Todos los clientes» muestra todos.")
        if vista != pedida:
            st.query_params["vista"] = vista
        n = total if vista == INTERNO else clientes[vista]
        nombre = "Equipo Contex" if vista == INTERNO else nombre_corto(vista)
        rol = (f"Vista interna · {n} pedidos" if vista == INTERNO
               else f"Vista del cliente · {n} pedido{'s' if n != 1 else ''}")
        st.markdown(f'<div class="cuenta"><div class="avatar">{vistas.esc(iniciales(nombre))}</div>'
                    f'<div><b>{vistas.esc(nombre)}</b><span>{rol}</span></div></div>',
                    unsafe_allow_html=True)

        # Costos y márgenes son información interna: un cliente nunca los ve.
        paginas = list(MENU) if vista == INTERNO else ["Tablero", "Lista de pedidos"]
        if st.session_state.get("pagina") not in paginas:
            st.session_state["pagina"] = paginas[0]
        actual = st.session_state["pagina"]
        en_detalle = bool(parametro("pedido"))
        st.markdown('<div class="rail-etiqueta">Menú</div>', unsafe_allow_html=True)
        for nombre_pagina in paginas:
            st.button(nombre_pagina, key=f"nav_{nombre_pagina}", icon=MENU[nombre_pagina],
                      type="primary" if (nombre_pagina == actual and not en_detalle) else "secondary",
                      on_click=ir_a, args=(nombre_pagina,), width="stretch")

        clase = "punto" if es_demo else "punto real"
        texto = "Datos de demostración" if es_demo else f"Conectado · {fuente}"
        st.markdown(f'<div class="rail-pie"><span class="{clase}"></span>{vistas.esc(texto)}</div>',
                    unsafe_allow_html=True)
        if st.button("Actualizar datos", key="actualizar", icon=":material/refresh:", width="stretch"):
            cargar.clear()
            st.rerun()
    return vista, actual


def cerrar_menu_si_hace_falta() -> None:
    if st.session_state.pop("cerrar_menu_movil", False):
        incrustar_html(CERRAR_MENU_MOVIL, 1)


def encabezado(titulo: str, subtitulo: str, fuente: str, es_demo: bool, ruta: str = "Seguimiento") -> None:
    clase = "fuente" if es_demo else "fuente real"
    etiqueta_fuente = "Datos de demostración" if es_demo else f"Conectado · {fuente}"
    hoy = date.today()
    st.markdown(
        f'<div class="titulo"><div><div class="ruta">Contex FYG / <b>{vistas.esc(ruta)}</b></div>'
        f'<h1>{vistas.esc(titulo)}</h1><p>{vistas.esc(subtitulo)}</p></div>'
        f'<div class="titulo-der"><span class="hoy">Hoy · {vistas.fecha_corta(hoy)}</span>'
        f'<span class="{clase}">{vistas.esc(etiqueta_fuente)}</span></div></div>',
        unsafe_allow_html=True,
    )


# --- Páginas ------------------------------------------------------------------

def boton_descargas(pedidos: list[Pedido], hoy: date, vista: str, es_demo: bool, dias: int, clave: str) -> None:
    """Un solo botón "Descargar" con el resumen en PDF y el Excel adentro."""
    alcance = "Todos los clientes" if vista == INTERNO else nombre_corto(vista)
    sello = f"{hoy:%Y%m%d}"
    archivo = "todos" if vista == INTERNO else nombre_corto(vista).lower().replace(" ", "_")
    with st.popover("Descargar", icon=":material/download:", width="stretch"):
        st.caption(f"{len(pedidos)} pedidos · {alcance}")
        st.download_button("Resumen en PDF", reportes.pdf_resumen(pedidos, hoy, alcance, es_demo, dias),
                           file_name=f"resumen_pedidos_{archivo}_{sello}.pdf", mime="application/pdf",
                           icon=":material/picture_as_pdf:", key=f"descarga_pdf_{clave}", width="stretch")
        st.download_button("Excel con detalle", reportes.excel_resumen(pedidos, hoy, alcance, dias),
                           file_name=f"pedidos_{archivo}_{sello}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           icon=":material/table_view:", key=f"descarga_xlsx_{clave}", width="stretch")


def cliente_whatsapp() -> tuple[whatsapp.WhatsAppCloud | None, str]:
    """(api, error de configuración). Una configuración mala se DICE, no cae a la demo callada."""
    try:
        return whatsapp.WhatsAppCloud.desde_config(seccion_de_secrets("whatsapp")), ""
    except whatsapp.ErrorWhatsApp as exc:
        return None, str(exc)


def incrustar_html(html: str, alto: int) -> None:
    """HTML con JavaScript propio. `st.iframe` en Streamlit nuevo; `components.html` en 1.50-1.6x."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=alto)
    else:  # pragma: no cover - versiones viejas de Streamlit
        import streamlit.components.v1 as components
        components.html(html, height=alto)


A_MI = "Mi número (prueba)"
A_CLIENTE = "Cliente"


@st.dialog("Enviar por WhatsApp", width="large")
def dialogo_whatsapp(titulo: str, telefono_inicial: str, texto: str, variables: list[str],
                     documentos: list[whatsapp.Documento], clave: str) -> None:
    api, error_config = cliente_whatsapp()
    config = seccion_de_secrets("whatsapp")
    numero_pruebas = str(config.get("numero_pruebas", "") or "")
    solo_pruebas = str(config.get("solo_pruebas", "")).strip().lower() in ("true", "1", "si", "sí")

    st.markdown(f"**{titulo}**")
    destino = st.segmented_control(
        "Enviar a", [A_MI, A_CLIENTE], default=A_MI, key=f"wsp_destino_{clave}", width="stretch",
        help="Primero envíatelo a ti para ver cómo llega. Cuando estés conforme, envíalo al cliente.")
    destino = destino or A_MI
    if destino == A_MI:
        telefono_txt = st.text_input("Tu número de WhatsApp", value=numero_pruebas,
                                     placeholder="987 654 321", icon=":material/person:",
                                     key=f"wsp_tel_yo_{clave}")
    else:
        telefono_txt = st.text_input("Número de WhatsApp del cliente", value=telefono_inicial,
                                     placeholder="987 654 321  o  +51 987 654 321",
                                     icon=":material/call:", key=f"wsp_tel_{clave}")
    telefono = whatsapp.normalizar_telefono(telefono_txt)
    if telefono_txt and not telefono:
        st.warning("Ese número no parece válido. Escribe el celular con 9 dígitos o con código de país.")
    bloqueado = destino == A_CLIENTE and solo_pruebas
    if bloqueado:
        st.warning("**Modo pruebas activo** (`solo_pruebas = true` en Secrets): por ahora solo se puede "
                   "enviar a tu número. Quítalo cuando la plantilla esté aprobada y probada.")

    st.markdown('<div class="wsp-burbuja">' + vistas.esc(texto).replace("\n", "<br>")
                .replace("*", "") + "</div>", unsafe_allow_html=True)
    adjuntos = " ".join(f'<span class="wsp-adjunto">📎 {vistas.esc(d.nombre)}</span>' for d in documentos)
    st.markdown(f'<div class="wsp-adjuntos">{adjuntos}</div>', unsafe_allow_html=True)

    etiqueta_boton = "Enviarme la prueba" if destino == A_MI else "Enviar al cliente"
    if error_config:
        st.error(f"**La configuración de WhatsApp tiene un problema.** {error_config}")
    if api is not None:
        if st.button(etiqueta_boton, type="primary", icon=":material/send:", width="stretch",
                     disabled=not telefono or bloqueado, key=f"wsp_enviar_{clave}"):
            with st.spinner("Enviando por WhatsApp…"):
                resultado = api.enviar_avance(telefono, texto, variables, documentos)
            for paso in resultado.pasos:
                {"ok": st.success, "aviso": st.warning, "error": st.error}[paso.estado](
                    f"**{paso.nombre}:** {paso.detalle}")
            if resultado.enviado:
                st.session_state.setdefault("envios_wsp", []).append(
                    {"Hora": datetime.now().strftime("%H:%M:%S"), "Envío": titulo, "Destino": destino,
                     "Número": "+" + telefono,
                     "Resultado": ", ".join(f"{p.nombre}: {p.estado}" for p in resultado.pasos)})
                if destino == A_MI:
                    st.info("Revisa tu WhatsApp. Si el mensaje te llegó bien, cambia arriba a **Cliente**.")
    else:
        st.info("**Prueba sin configurar nada.** El botón verde abre el menú *Compartir* del celular con "
                "el mensaje, el PDF y el Excel: elige **WhatsApp** y luego **tu propio chat** (o el del "
                "cliente). Cuando se conecte la API de WhatsApp Business, el envío será directo con un clic.")
        incrustar_html(vistas.boton_compartir(texto, documentos, whatsapp.enlace_wa_me(telefono, texto)), 118)
        st.link_button("Solo el texto (abrir WhatsApp)", whatsapp.enlace_wa_me(telefono, texto),
                       icon=":material/chat:", width="stretch")
        with st.expander("Descargar los archivos"):
            columnas = st.columns(len(documentos))
            for col, doc in zip(columnas, documentos):
                with col:
                    st.download_button(doc.nombre, doc.contenido, file_name=doc.nombre, mime=doc.mime,
                                       icon=":material/download:", width="stretch",
                                       key=f"wsp_doc_{clave}_{doc.nombre}")

    envios = st.session_state.get("envios_wsp", [])
    if envios:
        with st.expander(f"Envíos de esta sesión ({len(envios)})"):
            st.dataframe(pd.DataFrame(envios[::-1]), hide_index=True, width="stretch")


def abrir_whatsapp_de_pedido(p: Pedido, hoy: date, es_demo: bool, dias: int) -> None:
    documentos = [
        whatsapp.Documento(reportes.pdf_pedido(p, hoy, es_demo, dias), f"Pedido_{p.codigo}.pdf", whatsapp.MIME_PDF),
        whatsapp.Documento(reportes.excel_resumen([p], hoy, nombre_corto(p.cliente), dias),
                           f"Pedido_{p.codigo}.xlsx", whatsapp.MIME_XLSX),
    ]
    dialogo_whatsapp(f"{p.codigo} · {nombre_corto(p.cliente)}", p.telefono,
                     whatsapp.mensaje_de_avance(p, hoy, dias),
                     whatsapp.variables_de_plantilla(p, hoy, dias), documentos, p.codigo)


def abrir_whatsapp_de_cliente(cliente: str, pedidos: list[Pedido], hoy: date, es_demo: bool, dias: int) -> None:
    corto = nombre_corto(cliente)
    archivo = corto.replace(" ", "_")
    documentos = [
        whatsapp.Documento(reportes.pdf_resumen(pedidos, hoy, corto, es_demo, dias),
                           f"Resumen_{archivo}.pdf", whatsapp.MIME_PDF),
        whatsapp.Documento(reportes.excel_resumen(pedidos, hoy, corto, dias),
                           f"Pedidos_{archivo}.xlsx", whatsapp.MIME_XLSX),
    ]
    contacto = next((p.contacto for p in pedidos if p.contacto), corto)
    telefono = next((p.telefono for p in pedidos if p.telefono), "")
    activos = [p for p in pedidos if not p.entregado]
    principal = min(activos or pedidos, key=lambda p: p.fecha_entrega)
    variables = whatsapp.variables_de_plantilla(principal, hoy, dias)
    dialogo_whatsapp(f"Resumen de {corto} · {len(pedidos)} pedido(s)", telefono,
                     whatsapp.mensaje_de_resumen(contacto, pedidos, hoy, dias), variables, documentos,
                     f"cliente_{archivo}")


def pagina_tablero(pedidos: list[Pedido], hoy: date, vista: str, dias: int, es_demo: bool) -> None:
    with st.container(key="herramientas"):
        anchos = [5, 3, 1.4] if vista == INTERNO else [4.2, 3, 1.4, 1.6]
        busqueda_col, periodo_col, descarga_col, *wsp_col = st.columns(anchos, gap="small")
        with busqueda_col:
            busqueda = st.text_input("Buscar", placeholder="Buscar por código, cliente o producto…",
                                     label_visibility="collapsed", icon=":material/search:")
        with periodo_col:
            periodo = st.segmented_control("Entregados", ["Últimos 30 días", "Todo el historial"],
                                           default="Últimos 30 días", label_visibility="collapsed",
                                           width="stretch")
        dias_entregado = None if periodo == "Todo el historial" else 30
    if busqueda:
        b = busqueda.strip().lower()
        pedidos = [p for p in pedidos
                   if b in p.codigo.lower() or b in p.cliente.lower() or b in p.productos.lower()]
    with descarga_col:
        boton_descargas(pedidos, hoy, vista, es_demo, dias, "tablero")
    if wsp_col and pedidos:
        with wsp_col[0]:
            if st.button("WhatsApp", icon=":material/chat:", key="wsp_cliente", width="stretch",
                         help="Enviar al cliente el resumen de sus pedidos con el PDF y el Excel"):
                abrir_whatsapp_de_cliente(vista, pedidos, hoy, es_demo, dias)
    st.markdown(vistas.fila_indicadores(indicadores(pedidos, hoy, dias)), unsafe_allow_html=True)
    st.markdown(vistas.tablero(pedidos, hoy, vista, parametro("pedido"), dias, dias_entregado),
                unsafe_allow_html=True)
    st.caption("Toca una tarjeta para ver el detalle, el registro de cada etapa y su proforma.")


def pagina_detalle(p: Pedido, pedidos: list[Pedido], hoy: date, vista: str, dias: int, es_demo: bool) -> None:
    volver, wsp, descarga = st.columns([3.2, 1.6, 1.4])
    with volver:
        st.markdown(f'<div class="volver"><a href="{vistas.enlace(vista=vista)}" target="_self">'
                    '← Volver al tablero</a></div>', unsafe_allow_html=True)
    with wsp:
        if st.button("Enviar por WhatsApp", icon=":material/chat:", key="wsp_pedido", width="stretch"):
            abrir_whatsapp_de_pedido(p, hoy, es_demo, dias)
    with descarga:
        st.download_button("Proforma PDF" if p.con_precios else "Ficha en PDF",
                           reportes.pdf_pedido(p, hoy, es_demo, dias),
                           file_name=f"proforma_{p.codigo}.pdf", mime="application/pdf",
                           icon=":material/picture_as_pdf:", type="primary", key="descarga_proforma",
                           width="stretch")
    st.markdown(vistas.cabecera_pedido(p, hoy, dias), unsafe_allow_html=True)
    st.markdown(vistas.stepper(p), unsafe_allow_html=True)
    st.markdown(vistas.subetapas(p), unsafe_allow_html=True)

    izquierda, derecha = st.columns([3, 2], gap="large")
    with izquierda:
        st.markdown('<div class="seccion-t">Registro de la trazabilidad</div>', unsafe_allow_html=True)
        st.markdown(vistas.linea_de_tiempo(p), unsafe_allow_html=True)
    with derecha:
        st.markdown('<div class="seccion-t">Productos</div>', unsafe_allow_html=True)
        filas = [{"Producto": l.producto, "Cantidad": l.cantidad, "Precio unit.": l.precio_unitario,
                  "Importe": l.importe} for l in p.lineas]
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch",
                     column_config={"Precio unit.": st.column_config.NumberColumn(format="S/ %.2f"),
                                    "Importe": st.column_config.NumberColumn(format="S/ %.2f")})
        if p.con_precios:
            st.metric("Total con IGV", f"S/ {p.subtotal * (1 + reportes.IGV):,.2f}")
        if p.etapa in ("despacho", "entregado"):
            st.metric("Prendas entregadas", f"{p.cantidad_despachada} / {p.cantidad_total}")
        if p.no_conformes:
            st.warning(f"{p.no_conformes} salida(s) no conforme(s) en reproceso (ISO 8.7).")
        if p.encuesta is not None:
            st.metric("Satisfacción del cliente", f"{p.encuesta:.1f} / 5")
        otros = [x.codigo for x in pedidos]
        elegido = st.selectbox("Ir a otro pedido", otros, index=otros.index(p.codigo))
        if elegido != p.codigo:
            st.query_params["pedido"] = elegido
            st.rerun()


# --- Costos ----------------------------------------------------------------------

TODO = "Todo el historial"
FORMATO_SOLES = st.column_config.NumberColumn(format="accounting")  # 1,234.00 · montos en soles


def nombre_del_mes(periodo: str) -> str:
    """"2026-11" -> "Noviembre 2026"."""
    if periodo == TODO or len(periodo) != 7:
        return periodo
    meses = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
             "Octubre", "Noviembre", "Diciembre")
    return f"{meses[int(periodo[5:]) - 1]} {periodo[:4]}"


def tablas_con_ediciones(base: costos.TablasCosto) -> costos.TablasCosto:
    """Las tablas de la fuente + lo editado en la sesión (tarifas y CIF del mes)."""
    tarifas = {**base.tarifas, **st.session_state.get("costos_tarifas", {})}
    cif = base.cif.copy()
    for periodo, df in st.session_state.get("costos_cif", {}).items():
        cif = pd.concat([cif[cif["periodo"].astype(str).str[:7] != periodo], df.assign(periodo=periodo)],
                        ignore_index=True)
    return costos.TablasCosto(base.materiales, base.mano_obra, base.terceros, cif, tarifas)


def pagina_costos(pedidos: list[Pedido], hoy: date, config: dict, fuente: str, es_demo: bool) -> None:
    encabezado("Costos de producción", "Costo real por orden de trabajo, centros de costo y cierre mensual",
               fuente, es_demo, ruta="Costos")
    try:
        base = cargar_costos(json.dumps(config, sort_keys=True, default=str))
    except Exception as exc:  # la fuente respondió mal: se dice, no se cae
        st.error(f"No se pudieron leer los costos: {exc}")
        return
    if base is None:
        st.info("La fuente de datos todavía no tiene las consultas de costos. Agrega `costos_materiales`, "
                "`costos_mano_obra`, `costos_terceros` y `costos_cif` en `[datos.consultas]` (ver «Conexión "
                "de datos»). Con los datos de demostración este módulo funciona completo.")
        return
    tablas = tablas_con_ediciones(base)
    lista_periodos = costos.periodos(tablas)

    c1, c2, c3 = st.columns([2, 2.4, 1.3])
    with c1:
        periodo_txt = st.selectbox("Periodo", [TODO] + lista_periodos, index=0, key="costos_periodo",
                                   format_func=nombre_del_mes)
    with c2:
        base_clave = st.selectbox("Asignar costos indirectos por", list(costos.BASES), key="costos_base",
                                  format_func=costos.BASES.get,
                                  help="Regla para repartir los CIF de cada centro de costo entre las OT.")
    periodo = None if periodo_txt == TODO else periodo_txt
    res = costos.costear(pedidos, tablas, periodo, base_clave, hoy)
    with c3:
        st.markdown('<div style="height:1.75rem"></div>', unsafe_allow_html=True)
        st.download_button("Excel de costos", costos.excel_cierre(res), icon=":material/download:",
                           file_name=f"costos_{res.periodo.replace(' ', '_')}.xlsx", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="costos_excel")

    if res.por_ot.empty:
        st.info("No hay movimientos de costo en este periodo.")
        return
    st.markdown(vistas.fila_indicadores_costos(res.kpis, res.periodo), unsafe_allow_html=True)
    resumen, por_ot, centros, cierre, maestros = st.tabs(
        ["Resumen", "Por orden de trabajo", "Centros de costo y CIF", "Cierre mensual", "Tablas maestras"])

    with resumen:
        izq, der = st.columns([1.15, 1], gap="medium")
        with izq:
            st.markdown(vistas.estructura_del_costo(res.kpis["elementos"]), unsafe_allow_html=True)
        with der:
            filas = [(r["Centro"], r["Total"]) for r in res.por_proceso.sort_values("Total", ascending=False)
                     .to_dict("records")]
            st.markdown(vistas.barras_por_centro(filas, "Costo por centro de costo",
                                                 "Materia prima + mano de obra + terceros + CIF de cada centro"),
                        unsafe_allow_html=True)
        st.markdown('<div class="seccion-t">Costo y margen por orden de trabajo</div>', unsafe_allow_html=True)
        st.caption("Montos en soles (S/), sin IGV.")
        tabla = res.por_ot[["OT", "Cliente", "Unidades", "Costo", "Costo total", "Costo unitario",
                            "Venta (sin IGV)", "Margen %"]].copy()
        tabla["Margen %"] = tabla["Margen %"] * 100
        st.dataframe(tabla, hide_index=True, width="stretch", column_config={
            "Costo total": FORMATO_SOLES, "Costo unitario": FORMATO_SOLES, "Venta (sin IGV)": FORMATO_SOLES,
            "Margen %": st.column_config.NumberColumn(format="%.1f %%", help="Solo OT que ya salieron de producción"),
            "Costo": st.column_config.TextColumn(help="«En proceso»: costo acumulado hasta hoy, sin margen"),
        })
        bajos = res.por_ot[res.por_ot["Margen %"] < costos.MARGEN_MINIMO]
        for r in bajos.to_dict("records"):
            st.warning(f"**{r['OT']}** ({r['Cliente']}) tiene margen de **{r['Margen %']:.1%}**, debajo del "
                       f"mínimo de {costos.MARGEN_MINIMO:.0%}. Revisa su detalle en «Por orden de trabajo».")

    with por_ot:
        opciones = res.por_ot["OT"].tolist()
        info = {p.codigo: p for p in pedidos}
        elegido = st.selectbox("Orden de trabajo", opciones, key="costos_ot",
                               format_func=lambda c: f"{c} · {nombre_corto(info[c].cliente)} · {info[c].productos}")
        fila = res.por_ot[res.por_ot["OT"] == elegido].iloc[0]
        det = costos.detalle_ot(res, elegido)
        a, b, c, d = st.columns(4)
        a.metric("Costo total", vistas.soles(fila["Costo total"]))
        b.metric("Costo unitario", vistas.soles(fila["Costo unitario"]), help=f"{int(fila['Unidades'])} unidades")
        c.metric("Venta (sin IGV)", vistas.soles(fila["Venta (sin IGV)"]) if pd.notna(fila["Venta (sin IGV)"]) else "—")
        d.metric("Margen", f"{fila['Margen %']:.1%}" if pd.notna(fila["Margen %"]) else fila["Costo"])
        st.markdown(vistas.estructura_del_costo({e: float(fila[e]) for e in costos.ELEMENTOS}),
                    unsafe_allow_html=True)
        ver_mp, ver_te, ver_mo, ver_cif, ver_desv = st.tabs(
            ["Materia prima", "Terceros", "Mano de obra", "CIF asignado", "Desvíos vs ficha técnica"])
        mon = {k: FORMATO_SOLES for k in ("Costo unit.", "Costo", "Tarifa/h", "Monto", "Asignado", "Valor del desvío")}
        mon["Fecha"] = st.column_config.DatetimeColumn(format="DD/MM/YYYY")
        with ver_mp:
            st.dataframe(det["materiales"].drop(columns=["OT"]), hide_index=True, width="stretch", column_config=mon)
        with ver_te:
            st.dataframe(det["terceros"].drop(columns=["OT"]), hide_index=True, width="stretch", column_config=mon)
        with ver_mo:
            st.dataframe(det["mano_obra"].drop(columns=["OT"]), hide_index=True, width="stretch", column_config=mon)
        with ver_cif:
            cif_ot = det["cif"].drop(columns=["OT"]).copy()
            cif_ot["% de la base"] = cif_ot["% de la base"] * 100
            st.dataframe(cif_ot, hide_index=True, width="stretch",
                         column_config={**mon, "% de la base": st.column_config.NumberColumn(format="%.1f %%")})
        with ver_desv:
            dv = det["desvios"].drop(columns=["OT"]).copy()
            dv["Desvío %"] = dv["Desvío %"] * 100
            st.caption("Lo usado (consumo + merma) contra lo que pedía la ficha técnica. Positivo = se usó de más.")
            st.dataframe(dv, hide_index=True, width="stretch",
                         column_config={**mon, "Desvío %": st.column_config.NumberColumn(format="%+.1f %%")})
        st.download_button("Reporte de costo de la OT (PDF)",
                           costos.pdf_costo_ot(res, elegido, info[elegido], hoy, es_demo),
                           file_name=f"costo_{elegido}.pdf", mime="application/pdf", type="primary",
                           icon=":material/picture_as_pdf:", key="costos_pdf_ot")

    with centros:
        st.markdown('<div class="seccion-t">Costo por centro de costo</div>', unsafe_allow_html=True)
        st.dataframe(res.por_proceso, hide_index=True, width="stretch",
                     column_config={e: FORMATO_SOLES for e in list(costos.ELEMENTOS) + ["Total"]})
        st.markdown('<div class="seccion-t">Costos indirectos del mes (CIF)</div>', unsafe_allow_html=True)
        if periodo is None:
            st.info("Elige un **mes** arriba para ver y editar sus costos indirectos.")
        else:
            cif_mes = tablas.cif[tablas.cif["periodo"].astype(str).str[:7] == periodo][["centro", "concepto", "monto"]]
            st.caption("Gastos que no se pueden atribuir a una prenda (alquiler, energía, jefatura…). Edítalos y "
                       "el costo de cada OT se recalcula al instante. «Centro»: " +
                       ", ".join(f"{k} = {v}" for k, v in costos.CENTROS.items()))
            editado = st.data_editor(cif_mes.reset_index(drop=True), key=f"cif_editor_{periodo}", num_rows="dynamic",
                                     hide_index=True, width="stretch", column_config={
                                         "centro": st.column_config.SelectboxColumn("Centro", options=list(costos.CENTROS),
                                                                                    required=True),
                                         "concepto": st.column_config.TextColumn("Concepto", required=True),
                                         "monto": st.column_config.NumberColumn("Monto (S/)", format="accounting", min_value=0)})
            guardado = st.session_state.get("costos_cif", {}).get(periodo)
            if not editado.equals(cif_mes.reset_index(drop=True)) and (guardado is None or not editado.equals(guardado)):
                st.session_state.setdefault("costos_cif", {})[periodo] = editado.dropna(subset=["centro"])
                st.rerun()
            if res.kpis["cif_sin_asignar"]:
                st.warning(f"**{vistas.soles(res.kpis['cif_sin_asignar'])} de CIF quedaron sin asignar**: son de "
                           "centros donde ninguna OT tuvo actividad este mes con la base elegida. No se cargan a "
                           "otras OT para no inflar su costo.")
            st.markdown('<div class="seccion-t">Cómo se repartieron</div>', unsafe_allow_html=True)
            asig = res.asignacion.copy()
            asig["% de la base"] = asig["% de la base"] * 100
            st.dataframe(asig, hide_index=True, width="stretch", column_config={
                "Monto": FORMATO_SOLES, "Asignado": FORMATO_SOLES,
                "% de la base": st.column_config.NumberColumn(format="%.1f %%")})

    with cierre:
        pagina_cierre(res, periodo)

    with maestros:
        st.markdown('<div class="seccion-t">Tarifa por hora de mano de obra interna</div>', unsafe_allow_html=True)
        st.caption("Se usa cuando la liquidación no trae la tarifa. Corte, arreglos y limpieza se hacen en planta; "
                   "la confección, el bordado y el estampado suelen ir por orden de servicio a talleres externos.")
        tarifas_df = pd.DataFrame([{"Proceso": k, "Nombre": costos.PROCESOS.get(k, k), "Tarifa por hora": v}
                                   for k, v in tablas.tarifas.items()])
        ed = st.data_editor(tarifas_df, hide_index=True, width="stretch", key="editor_tarifas", column_config={
            "Proceso": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True),
            "Tarifa por hora": st.column_config.NumberColumn("Tarifa por hora (S/)", format="accounting", min_value=0)})
        nuevas = dict(zip(ed["Proceso"], ed["Tarifa por hora"]))
        if nuevas != tablas.tarifas:
            st.session_state["costos_tarifas"] = nuevas
            st.rerun()
        st.markdown('<div class="seccion-t">Centros de costo</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Código": k, "Centro de costo": v,
                                    "Tipo": "Apoyo (se reparte entre todas las OT)" if k == costos.CENTRO_APOYO
                                    else "Productivo (solo a las OT que pasan por él)"}
                                   for k, v in costos.CENTROS.items()]), hide_index=True, width="stretch")
        st.caption("Los cambios de esta pantalla viven en la sesión mientras no se conecte la base de datos: "
                   "descarga el Excel o cierra el periodo para guardarlos.")


def pagina_cierre(res: costos.Resultado, periodo: str | None) -> None:
    if periodo is None:
        st.info("El cierre es **por mes**: elige un periodo arriba.")
        return
    cierres = st.session_state.setdefault("costos_cierres", {})
    cerrado = cierres.get(periodo)
    k = res.kpis
    st.markdown(f'<div class="seccion-t">Cierre de costos · {nombre_del_mes(periodo)}</div>', unsafe_allow_html=True)
    revision = [
        ("OT con costo en el mes", k["ots"] > 0, f"{k['ots']} órdenes de trabajo"),
        ("Costos indirectos cargados", k["cif_total"] > 0, vistas.soles(k["cif_total"])),
        ("CIF totalmente asignado", k["cif_sin_asignar"] < 0.01,
         "todo asignado" if k["cif_sin_asignar"] < 0.01 else f"{vistas.soles(k['cif_sin_asignar'])} sin asignar"),
        ("Merma bajo 5 % del consumo", (k["merma_pct"] or 0) < 0.05,
         "—" if k["merma_pct"] is None else f"{k['merma_pct']:.1%}"),
    ]
    for nombre, ok, detalle in revision:
        st.markdown(f"{'✅' if ok else '⚠️'} **{nombre}** — {detalle}")
    if cerrado:
        st.success(f"**Periodo cerrado** el {cerrado['fecha']} · costo total {vistas.soles(cerrado['costo_total'])} "
                   f"· base de CIF: {costos.BASES[cerrado['base']]}. Las cifras del cierre quedan congeladas en su Excel.")
        st.download_button(f"Excel del cierre {periodo}", cerrado["excel"], file_name=f"cierre_costos_{periodo}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           icon=":material/lock:", type="primary", key="cierre_excel")
        st.button("Reabrir el periodo", key="reabrir", on_click=lambda: cierres.pop(periodo, None))
        return

    def cerrar():
        marca = datetime.now().strftime("%d/%m/%Y %H:%M")
        cierres[periodo] = {"fecha": marca, "base": res.base, "costo_total": k["costo_total"],
                            "excel": costos.excel_cierre(res, cerrado=f"cerrado el {marca}")}

    st.button(f"Cerrar el periodo {periodo}", type="primary", icon=":material/lock:", on_click=cerrar, key="cerrar",
              help="Congela el costo de cada OT del mes, la asignación de CIF y genera el Excel del cierre.")


def tabla_de_pedidos(pedidos: list[Pedido], hoy: date, dias: int) -> pd.DataFrame:
    filas = []
    for p in pedidos:
        texto, _ = etiqueta(p, hoy, dias)
        filas.append({
            "Código": p.codigo, "Cliente": p.cliente, "Productos": p.productos,
            "Prendas": p.cantidad_total, "Etapa": ETAPAS_POR_CLAVE[p.etapa].nombre, "Estado": texto,
            "Avance producción": p.avance_produccion, "Fecha pedido": p.fecha_pedido,
            "Entrega": p.fecha_entrega, "Entregado": p.fecha_entregado,
            "Alerta": "Sí" if (en_riesgo(p, hoy, dias) or atrasado(p, hoy)) else "",
        })
    return pd.DataFrame(filas)


def pagina_lista(pedidos: list[Pedido], hoy: date, vista: str, dias: int, es_demo: bool) -> None:
    df = tabla_de_pedidos(pedidos, hoy, dias)
    st.caption("Aquí están **todos** los pedidos, también los entregados hace más de 30 días.")
    if df.empty:
        st.info("No hay pedidos para mostrar.")
        return
    etapas = st.pills("Etapa", list(dict.fromkeys(df["Etapa"])), selection_mode="multi",
                      label_visibility="collapsed")
    if etapas:
        df = df[df["Etapa"].isin(etapas)]
    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "Avance producción": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
            "Fecha pedido": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Entrega": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Entregado": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
    )
    elegidos = [p for p in pedidos if p.codigo in set(df["Código"])]
    _, descarga = st.columns([4, 1.4])
    with descarga:
        boton_descargas(elegidos, hoy, vista, es_demo, dias, "lista")
    codigos = df["Código"].tolist()
    elegido = st.selectbox("Abrir el detalle de", codigos, index=None, placeholder="Elige un pedido…")
    if elegido:
        st.query_params.update({"pedido": elegido, "vista": vista})
        st.rerun()


def pagina_conexion(config: dict, fuente: str, es_demo: bool, avisos: list[str]) -> None:
    if es_demo:
        st.info("La app está mostrando **datos de demostración**. Cuando se conecte la base del "
                "cliente, el tablero se llena solo con sus pedidos: no hay que cambiar código.")
    else:
        st.success(f"Conectado a: **{fuente}**")
    if avisos:
        with st.expander(f"{len(avisos)} aviso(s) al leer los datos", expanded=True):
            for a in avisos:
                st.write("• " + a)
    if st.button("Probar conexión"):
        try:
            st.success(obtener_conector(config).probar())
        except Exception as exc:  # la pantalla tiene que decir qué falló, no caerse
            st.error(f"No se pudo leer la fuente: {exc}")

    st.subheader("Qué tiene que devolver la base de datos")
    st.write("Tres consultas, una por tabla. Pueden ser vistas o SELECT con joins: "
             "solo importa que traigan estas columnas.")
    for tabla, cols in COLUMNAS.items():
        st.markdown(f"**{tabla}** — obligatorias: `{'`, `'.join(cols['obligatorias'])}`"
                    + (f" · opcionales: `{'`, `'.join(cols['opcionales'])}`" if cols["opcionales"] else ""))
    st.caption("Etapas válidas: recibido, produccion, inspeccion, despacho, entregado "
               "(también se aceptan 'Producción', 'Calidad', 'Entregada'…).")
    st.markdown("**Módulo de costos** (opcional): cuatro consultas más, que salen de la liquidación de órdenes "
                "de proceso y del kardex del ERP.")
    for tabla, cols in costos.COLUMNAS.items():
        st.markdown(f"**costos_{tabla}** — `{'`, `'.join(cols)}`")
    st.caption("Procesos: COR corte, BOR bordado, EST estampado, CNF confección, LAV lavado, ARR arreglos, "
               "ACA limpieza y acabado. Centros de costo: los mismos códigos + PLA (planta general, apoyo).")
    st.subheader("Cómo se configura (Secrets de Streamlit Cloud)")
    st.code('''[datos]
conector = "sql"
url = "postgresql+psycopg2://usuario:clave@servidor:5432/produccion"
dias_produccion = 15

[datos.consultas]
pedidos = "SELECT codigo, cliente, etapa, fecha_pedido, fecha_entrega, avance_produccion, no_conformes, cantidad_despachada, liberado, encuesta, fecha_entregado FROM v_pedidos"
lineas  = "SELECT codigo_pedido, producto, cantidad FROM v_pedido_lineas"
eventos = "SELECT codigo_pedido, fecha, etapa, clausula, descripcion, responsable, evidencia FROM v_pedido_eventos"
costos_materiales = "SELECT codigo_pedido, fecha, proceso, codigo, descripcion, um, cant_requerida, cant_consumida, cant_merma, costo_unitario FROM v_liquidacion_mp"
costos_mano_obra  = "SELECT codigo_pedido, fecha, proceso, personal, horas, tarifa_hora FROM v_liquidacion_mo"
costos_terceros   = "SELECT codigo_pedido, fecha, proceso, proveedor, cantidad, costo_unitario FROM v_ordenes_servicio"
costos_cif        = "SELECT periodo, centro, concepto, monto FROM v_cif_mensual"''',
            language="toml")


# --- Principal ----------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Contex FYG · Trazabilidad",
                       page_icon=str(LOGO) if LOGO.exists() else "🧵", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    config = config_de_datos()
    try:
        dias = int(config.get("dias_produccion", DIAS_PRODUCCION_POR_DEFECTO))
    except (TypeError, ValueError):
        dias = DIAS_PRODUCCION_POR_DEFECTO
    try:
        pedidos, avisos, fuente, es_demo = cargar(json.dumps(config, sort_keys=True, default=str))
    except (ErrorDeDatos, Exception) as exc:
        st.error(f"No se pudieron leer los pedidos: {exc}")
        st.caption("Revisa la sección [datos] de Secrets o quítala para volver a la demo.")
        return

    hoy = date.today()
    clientes: dict[str, int] = {}
    for p in pedidos:
        clientes[p.cliente] = clientes.get(p.cliente, 0) + 1
    vista, pagina = barra_lateral(clientes, fuente, es_demo)
    cerrar_menu_si_hace_falta()
    visibles = pedidos if vista == INTERNO else [p for p in pedidos if p.cliente == vista]

    codigo = parametro("pedido")
    elegido = next((p for p in visibles if p.codigo == codigo), None)
    if elegido is not None:
        encabezado(f"Pedido {elegido.codigo}", "Trazabilidad completa, etapa por etapa", fuente, es_demo,
                   ruta="Detalle del pedido")
        pagina_detalle(elegido, visibles, hoy, vista, dias, es_demo)
        return
    if codigo:
        st.query_params.pop("pedido", None)

    if pagina == "Costos" and vista == INTERNO:
        pagina_costos(pedidos, hoy, config, fuente, es_demo)
        return
    if pagina == "Conexión de datos":
        encabezado("Conexión de datos", "De dónde salen los pedidos del tablero", fuente, es_demo,
                   ruta="Conexión de datos")
        pagina_conexion(config, fuente, es_demo, avisos)
        return

    subtitulo = ("Seguimiento de todos los pedidos en curso" if vista == INTERNO
                 else f"Así van los pedidos de {nombre_corto(vista)}")
    encabezado("Seguimiento de pedidos", subtitulo, fuente, es_demo, ruta=pagina)
    if pagina == "Lista de pedidos":
        pagina_lista(visibles, hoy, vista, dias, es_demo)
    else:
        pagina_tablero(visibles, hoy, vista, dias, es_demo)


if __name__ == "__main__":
    main()
