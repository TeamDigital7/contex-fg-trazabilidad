"""Contex · Trazabilidad de pedidos.

Tablero para que el cliente vea cómo va su pedido, etapa por etapa, con el
registro ISO que deja cada una. Sin configuración usa datos de demostración;
con la sección [datos] en Secrets lee la base de datos real (ver README).
"""

from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from trazabilidad import vistas
from trazabilidad.conectores import COLUMNAS, ErrorDeDatos, obtener_conector, pedidos_desde_tablas
from trazabilidad.estilos import CSS
from trazabilidad.modelo import (DIAS_PRODUCCION_POR_DEFECTO, ETAPAS_POR_CLAVE, Pedido,
                                 atrasado, en_riesgo, etiqueta, indicadores)

INTERNO = "Equipo Contex (todo)"


# --- Datos --------------------------------------------------------------------

def config_de_datos() -> dict:
    """La sección [datos] de Secrets, o {} si no hay Secrets (demo)."""
    try:
        datos = st.secrets.get("datos", {})
    except Exception:  # sin archivo de secrets: es el caso normal de la demo
        return {}
    return json.loads(json.dumps(datos, default=dict)) if datos else {}


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
    "Conexión de datos": ":material/database:",
}
LOGO = Path(__file__).parent / "assets" / "logo_contex.png"


@st.cache_data
def logo_base64() -> str:
    return base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""


def ir_a(pagina: str) -> None:
    """on_click del menú: un clic, un rerun."""
    st.session_state["pagina"] = pagina
    st.query_params.pop("pedido", None)


def iniciales(nombre: str) -> str:
    palabras = [w for w in nombre.replace("(demo)", "").split() if w[:1].isalpha()]
    return "".join(w[0] for w in palabras[:2]).upper() or "CX"


def barra_lateral(clientes: list[str], fuente: str, es_demo: bool) -> tuple[str, str]:
    with st.sidebar:
        logo = logo_base64()
        if logo:
            st.markdown(f'<div class="logo-caja"><img src="data:image/png;base64,{logo}" alt="Contex FYG"></div>',
                        unsafe_allow_html=True)
        st.markdown('<div class="app-nombre"><b>Trazabilidad de pedidos</b>'
                    '<span>Seguimiento ISO 9001</span></div>', unsafe_allow_html=True)

        opciones = [INTERNO] + clientes
        pedida = parametro("vista")
        indice = opciones.index(pedida) if pedida in opciones else 0
        vista = st.selectbox("Ver como", opciones, index=indice,
                             help="Así ve el tablero cada cliente: solo sus pedidos.")
        if vista != pedida:
            st.query_params["vista"] = vista
        nombre = "Equipo Contex" if vista == INTERNO else vista.replace(" (demo)", "")
        rol = "Vista interna · todos los pedidos" if vista == INTERNO else "Vista del cliente"
        st.markdown(f'<div class="cuenta"><div class="avatar">{vistas.esc(iniciales(nombre))}</div>'
                    f'<div><b>{vistas.esc(nombre)}</b><span>{rol}</span></div></div>',
                    unsafe_allow_html=True)

        paginas = list(MENU) if vista == INTERNO else list(MENU)[:2]
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

def pagina_tablero(pedidos: list[Pedido], hoy: date, vista: str, dias: int) -> None:
    busqueda = st.text_input("Buscar", placeholder="Código, cliente o producto…",
                             label_visibility="collapsed")
    if busqueda:
        b = busqueda.strip().lower()
        pedidos = [p for p in pedidos
                   if b in p.codigo.lower() or b in p.cliente.lower() or b in p.productos.lower()]
    st.markdown(vistas.fila_indicadores(indicadores(pedidos, hoy, dias)), unsafe_allow_html=True)
    st.markdown(vistas.tablero(pedidos, hoy, vista, parametro("pedido"), dias), unsafe_allow_html=True)
    st.caption("Toca una tarjeta para ver el detalle y el registro de cada etapa.")


def pagina_detalle(p: Pedido, pedidos: list[Pedido], hoy: date, vista: str, dias: int) -> None:
    st.markdown(f'<div class="volver"><a href="{vistas.enlace(vista=vista)}" target="_self">'
                '← Volver al tablero</a></div>', unsafe_allow_html=True)
    st.markdown(vistas.cabecera_pedido(p, hoy, dias), unsafe_allow_html=True)
    st.markdown(vistas.stepper(p), unsafe_allow_html=True)
    st.markdown(vistas.subetapas(p), unsafe_allow_html=True)

    izquierda, derecha = st.columns([3, 2], gap="large")
    with izquierda:
        st.markdown('<div class="seccion-t">Registro de la trazabilidad</div>', unsafe_allow_html=True)
        st.markdown(vistas.linea_de_tiempo(p), unsafe_allow_html=True)
    with derecha:
        st.markdown('<div class="seccion-t">Productos</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Producto": l.producto, "Cantidad": l.cantidad} for l in p.lineas]),
                     hide_index=True, width="stretch")
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


def pagina_lista(pedidos: list[Pedido], hoy: date, vista: str, dias: int) -> None:
    df = tabla_de_pedidos(pedidos, hoy, dias)
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
    st.download_button("Descargar CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"pedidos_{hoy:%Y%m%d}.csv", mime="text/csv")
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
    st.subheader("Cómo se configura (Secrets de Streamlit Cloud)")
    st.code('''[datos]
conector = "sql"
url = "postgresql+psycopg2://usuario:clave@servidor:5432/produccion"
dias_produccion = 15

[datos.consultas]
pedidos = "SELECT codigo, cliente, etapa, fecha_pedido, fecha_entrega, avance_produccion, no_conformes, cantidad_despachada, liberado, encuesta, fecha_entregado FROM v_pedidos"
lineas  = "SELECT codigo_pedido, producto, cantidad FROM v_pedido_lineas"
eventos = "SELECT codigo_pedido, fecha, etapa, clausula, descripcion, responsable, evidencia FROM v_pedido_eventos"''',
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
    clientes = sorted({p.cliente for p in pedidos})
    vista, pagina = barra_lateral(clientes, fuente, es_demo)
    visibles = pedidos if vista == INTERNO else [p for p in pedidos if p.cliente == vista]

    codigo = parametro("pedido")
    elegido = next((p for p in visibles if p.codigo == codigo), None)
    if elegido is not None:
        encabezado(f"Pedido {elegido.codigo}", "Trazabilidad completa, etapa por etapa", fuente, es_demo,
                   ruta="Detalle del pedido")
        pagina_detalle(elegido, visibles, hoy, vista, dias)
        return
    if codigo:
        st.query_params.pop("pedido", None)

    if pagina == "Conexión de datos":
        encabezado("Conexión de datos", "De dónde salen los pedidos del tablero", fuente, es_demo,
                   ruta="Conexión de datos")
        pagina_conexion(config, fuente, es_demo, avisos)
        return

    subtitulo = ("Seguimiento de todos los pedidos en curso" if vista == INTERNO
                 else f"Así va su pedido, {vista.replace(' (demo)', '')}")
    encabezado("Seguimiento de pedidos", subtitulo, fuente, es_demo, ruta=pagina)
    if pagina == "Lista de pedidos":
        pagina_lista(visibles, hoy, vista, dias)
    else:
        pagina_tablero(visibles, hoy, vista, dias)


if __name__ == "__main__":
    main()
