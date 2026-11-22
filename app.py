"""Contex · Trazabilidad de pedidos.

Tablero para que el cliente vea cómo va su pedido, etapa por etapa, con el
registro ISO que deja cada una. Sin configuración usa datos de demostración;
con la sección [datos] en Secrets lee la base de datos real (ver README).
"""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

from trazabilidad import vistas
from trazabilidad.conectores import COLUMNAS, ErrorDeDatos, obtener_conector, pedidos_desde_tablas
from trazabilidad.estilos import CSS
from trazabilidad.modelo import (DIAS_PRODUCCION_POR_DEFECTO, ETAPAS_POR_CLAVE, Pedido,
                                 atrasado, en_riesgo, etiqueta, indicadores)

INTERNO = "Equipo Contex (todo)"
PAGINAS = ("Tablero", "Lista de pedidos", "Conexión de datos")


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


def barra_lateral(clientes: list[str], fuente: str, es_demo: bool) -> tuple[str, str]:
    with st.sidebar:
        st.markdown('<div class="marca">Contex<span>·</span>Trazabilidad</div>'
                    '<div class="marca-sub">Seguimiento de pedidos ISO 9001</div>',
                    unsafe_allow_html=True)
        opciones = [INTERNO] + clientes
        pedida = parametro("vista")
        indice = opciones.index(pedida) if pedida in opciones else 0
        vista = st.selectbox("Ver como", opciones, index=indice,
                             help="Así ve el tablero cada cliente: solo sus pedidos.")
        if vista != pedida:
            st.query_params["vista"] = vista
        paginas = PAGINAS if vista == INTERNO else PAGINAS[:2]
        pagina = st.radio("Sección", paginas, label_visibility="collapsed")
        st.divider()
        st.caption(("🧪 " if es_demo else "🔌 ") + fuente)
        if st.button("Actualizar datos", width="stretch"):
            cargar.clear()
            st.rerun()
    return vista, pagina


def encabezado(titulo: str, subtitulo: str, fuente: str, es_demo: bool) -> None:
    clase = "fuente" if es_demo else "fuente real"
    etiqueta_fuente = "DATOS DE DEMOSTRACIÓN" if es_demo else f"CONECTADO · {fuente}"
    st.markdown(
        f'<div class="titulo"><div><h1>{vistas.esc(titulo)}</h1><p>{vistas.esc(subtitulo)}</p></div>'
        f'<span class="{clase}">{vistas.esc(etiqueta_fuente)}</span></div>',
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
        st.subheader("Registro de la trazabilidad")
        st.markdown(vistas.linea_de_tiempo(p), unsafe_allow_html=True)
    with derecha:
        st.subheader("Productos")
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
    etapas = st.multiselect("Etapa", sorted(df["Etapa"].unique()), placeholder="Todas las etapas")
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
    st.set_page_config(page_title="Contex · Trazabilidad", page_icon="🧵", layout="wide")
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
        encabezado(f"Pedido {elegido.codigo}", "Trazabilidad completa, etapa por etapa", fuente, es_demo)
        pagina_detalle(elegido, visibles, hoy, vista, dias)
        return
    if codigo:
        st.query_params.pop("pedido", None)

    if pagina == "Conexión de datos":
        encabezado("Conexión de datos", "De dónde salen los pedidos del tablero", fuente, es_demo)
        pagina_conexion(config, fuente, es_demo, avisos)
        return

    subtitulo = ("Seguimiento de todos los pedidos en curso" if vista == INTERNO
                 else f"Así va su pedido, {vista.replace(' (demo)', '')}")
    encabezado("Seguimiento de pedidos", subtitulo, fuente, es_demo)
    if pagina == "Lista de pedidos":
        pagina_lista(visibles, hoy, vista, dias)
    else:
        pagina_tablero(visibles, hoy, vista, dias)


if __name__ == "__main__":
    main()
