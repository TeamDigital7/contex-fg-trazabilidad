"""Gráficos del dashboard (Altair / Vega-Lite), con el estilo de la app.

Sin Streamlit: cada función recibe datos y devuelve un gráfico de Altair. La
pantalla los dibuja con `theme=None` para que no se mezcle el tema de Streamlit.

Reglas (guía de visualización):
- color por la FUNCIÓN del dato: las series usan la paleta categórica validada en
  orden fijo (azul, naranja, aqua, amarillo); una sola magnitud usa un solo azul;
- un solo eje: ventas y costo comparten escala porque son la misma unidad (S/);
- líneas de 2 px, marcas de 8 px, grilla tenue, sin bordes de eje;
- siempre hay tooltip al pasar el mouse y etiquetas directas donde se decide algo.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

AZUL, NARANJA, AQUA, AMARILLO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
TEXTO, SUAVE, GRILLA = "#14213D", "#667085", "#EEF1F5"
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _mes_corto(m: str, en_curso: str | None = None) -> str:
    """"2026-11" -> "nov 26"; el mes que todavía no termina lleva asterisco."""
    return f"{MESES[int(m[5:]) - 1]} {m[2:4]}" + ("*" if m == en_curso else "")


def estilo(grafico: alt.Chart, alto: int = 260) -> alt.Chart:
    return (grafico.properties(height=alto, width="container", background="transparent")
            .configure(font="Inter, system-ui, sans-serif")
            .configure_view(stroke=None)
            .configure_axis(labelColor=SUAVE, titleColor=SUAVE, labelFontSize=11, titleFontSize=11,
                            gridColor=GRILLA, domain=False, tickColor=GRILLA, titleFontWeight=500)
            .configure_legend(orient="top", labelColor=TEXTO, labelFontSize=12, title=None, symbolSize=110,
                              columnPadding=14)
            .configure_text(color=TEXTO))


def ventas_y_costo(por_mes: pd.DataFrame, en_curso: str | None = None) -> alt.Chart:
    df = por_mes.copy()
    df["Mes corto"] = df["Mes"].map(lambda m: _mes_corto(m, en_curso))
    df["Margen texto"] = df["Margen %"].map(lambda v: "—" if v is None or pd.isna(v) else f"{v:.1%}")
    orden = df["Mes corto"].tolist()
    color = alt.Color("Serie:N", scale=alt.Scale(domain=["Ventas", "Costo real"], range=[AZUL, NARANJA]))
    tooltip = [alt.Tooltip("Mes corto:N", title="Mes"), alt.Tooltip("Ventas:Q", title="Ventas (S/)", format=",.0f"),
               alt.Tooltip("Costo:Q", title="Costo real (S/)", format=",.0f"),
               alt.Tooltip("Margen texto:N", title="Margen"), alt.Tooltip("Entregados:Q", title="Pedidos entregados")]
    base = alt.Chart(df).encode(x=alt.X("Mes corto:N", sort=orden, title=None,
                                        scale=alt.Scale(paddingInner=0.35),
                                        axis=alt.Axis(labelAngle=0, labelOverlap="greedy")))
    barras = base.transform_calculate(Serie="'Ventas'").mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        y=alt.Y("Ventas:Q", title="S/", axis=alt.Axis(format="~s")), color=color, tooltip=tooltip)
    linea = base.transform_calculate(Serie="'Costo real'").mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(
        size=60, filled=True, fill="white", strokeWidth=2)).encode(y="Costo:Q", color=color, tooltip=tooltip)
    return estilo(barras + linea, 280)


def cumplimiento(por_mes: pd.DataFrame, meta: float = 0.95, en_curso: str | None = None) -> alt.Chart:
    df = por_mes.copy()
    df["Mes corto"] = df["Mes"].map(lambda m: _mes_corto(m, en_curso))
    largo = df.melt(id_vars=["Mes corto", "Entregados"], value_vars=["A tiempo %", "Conformidad %"],
                    var_name="Serie", value_name="Valor").dropna(subset=["Valor"])
    largo["Serie"] = largo["Serie"].map({"A tiempo %": "Entregas a tiempo", "Conformidad %": "Producto conforme"})
    orden = df["Mes corto"].tolist()
    lineas = alt.Chart(largo).mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=60, filled=True)).encode(
        x=alt.X("Mes corto:N", sort=orden, title=None, axis=alt.Axis(labelAngle=0, labelOverlap="greedy")),
        y=alt.Y("Valor:Q", title=None, scale=alt.Scale(domain=[0.4, 1.02]), axis=alt.Axis(format=".0%")),
        color=alt.Color("Serie:N", scale=alt.Scale(domain=["Entregas a tiempo", "Producto conforme"],
                                                   range=[AZUL, NARANJA])),
        tooltip=[alt.Tooltip("Mes corto:N", title="Mes"), alt.Tooltip("Serie:N", title="Indicador"),
                 alt.Tooltip("Valor:Q", format=".0%"), alt.Tooltip("Entregados:Q", title="Entregas del mes")])
    # La meta va en el subtítulo de la tarjeta; aquí solo la línea punteada (un texto encima tapaba los puntos)
    regla = alt.Chart(pd.DataFrame({"y": [meta]})).mark_rule(strokeDash=[5, 4], color=SUAVE, strokeWidth=1.5).encode(
        y="y:Q", tooltip=[alt.Tooltip("y:Q", title="Meta", format=".0%")])
    return estilo(lineas + regla, 260)


def barras_horizontales(df: pd.DataFrame, categoria: str, valor: str, formato: str, titulo_valor: str,
                        regla: float | None = None, extra_tooltip: list | None = None, alto: int | None = None,
                        ordenar: bool = True) -> alt.Chart:
    """Una sola magnitud por categoría: un solo color, valor escrito al final de cada barra.

    `ordenar=False` respeta el orden recibido (p. ej. «Otros» siempre al final).
    """
    df = df.copy()
    orden = (df.sort_values(valor, ascending=False) if ordenar else df)[categoria].tolist()
    base = alt.Chart(df).encode(y=alt.Y(f"{categoria}:N", sort=orden, title=None,
                                        axis=alt.Axis(labelLimit=190, labelFontSize=11.5)))
    tooltip = [alt.Tooltip(f"{categoria}:N"), alt.Tooltip(f"{valor}:Q", title=titulo_valor, format=formato)]
    tooltip += extra_tooltip or []
    tope = float(df[valor].max() or 0) * 1.28 or 1  # aire a la derecha para la cifra
    barras = base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=AZUL, size=16).encode(
        x=alt.X(f"{valor}:Q", title=None, scale=alt.Scale(domain=[0, tope], nice=False),
                axis=alt.Axis(format=formato, labels=False, ticks=False, grid=False)),
        tooltip=tooltip)
    textos = base.mark_text(align="left", dx=5, fontSize=11.5, fontWeight=600, color=TEXTO).encode(
        x=f"{valor}:Q", text=alt.Text(f"{valor}:Q", format=formato))
    capas = barras + textos
    if regla is not None:
        capas += alt.Chart(pd.DataFrame({"x": [regla]})).mark_rule(strokeDash=[5, 4], color=SUAVE).encode(x="x:Q")
    return estilo(capas, alto or max(160, 34 * len(df)))


def pipeline(df: pd.DataFrame) -> alt.Chart:
    """Pedidos en curso por etapa, en el orden del proceso (no por tamaño)."""
    df = df.copy()
    df["Etapa (pedidos)"] = df["Etapa"] + " (" + df["Pedidos"].astype(str) + ")"
    orden = df["Etapa (pedidos)"].tolist()
    tope = float(df["Unidades"].max() or 0) * 1.45 or 1
    base = alt.Chart(df).encode(y=alt.Y("Etapa (pedidos):N", sort=orden, title=None, axis=alt.Axis(labelFontSize=11.5)))
    barras = base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=AZUL, size=18).encode(
        x=alt.X("Unidades:Q", title=None, scale=alt.Scale(domain=[0, tope], nice=False),
                axis=alt.Axis(labels=False, ticks=False, grid=False)),
        tooltip=[alt.Tooltip("Etapa:N"), alt.Tooltip("Pedidos:Q"), alt.Tooltip("Unidades:Q", title="Prendas", format=","),
                 alt.Tooltip("En riesgo:Q", title="En riesgo o atrasados")])
    textos = base.mark_text(align="left", dx=5, fontSize=11.5, color=TEXTO).encode(
        x="Unidades:Q", text=alt.Text("Unidades:Q", format=","))
    return estilo(barras + textos, 34 * len(df) + 20)
