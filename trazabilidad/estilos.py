"""Hoja de estilos de la app. Texto plano (NO f-string): las llaves van simples.

Colores de Contex FYG, sacados del logo: azul marino #12386B y gris #909090.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
  --marino: #12386B;          /* azul del logo */
  --marino-900: #0B2447;      /* rail del menú */
  --accion: #1F5FAF;          /* azul de acción, más claro que el del logo */
  --accion-suave: #E6EEF9;
  --gris-marca: #909090;      /* gris del logo */
  --fondo: #F3F5F9;
  --panel: #EAEEF4;
  --tarjeta: #FFFFFF;
  --borde: #DFE5EE;
  --texto: #14213D;
  --suave: #667085;
  --rojo-bg: #FDE8E7; --rojo: #B42318;
  --ambar-bg: #FEF3D6; --ambar: #93590A;
  --azul-bg: #E3EDFB; --azul: #1F5FAF;
  --verde-bg: #E3F4E8; --verde: #1D7A3E;
  --gris-bg: #EEF1F5; --gris: #4B5565;
  --mono: 'JetBrains Mono', ui-monospace, Menlo, monospace;
  --sombra: 0 1px 2px rgba(16,24,40,.05), 0 1px 3px rgba(16,24,40,.06);
}

html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', system-ui, sans-serif; }
[data-testid="stAppViewContainer"] { background: var(--fondo); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] [data-testid="stToolbarActions"], [data-testid="stDeployButton"],
[data-testid="stMainMenu"] { display: none; }
.block-container { padding-top: 1.6rem; max-width: 1560px; }

/* --- Encabezado ------------------------------------------------------------ */
.titulo { display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap;
          margin-bottom:1.1rem; }
.titulo .ruta { font-size:.78rem; color:var(--suave); font-weight:500; margin-bottom:.2rem; }
.titulo .ruta b { color:var(--marino); font-weight:600; }
.titulo h1 { font-size:1.6rem; font-weight:800; margin:0; padding:0; color:var(--texto); letter-spacing:-.02em; }
.titulo p { margin:.15rem 0 0; color:var(--suave); font-size:.9rem; }
.titulo-der { display:flex; gap:.5rem; align-items:center; flex-wrap:wrap; }
.fuente { font-size:.72rem; font-weight:600; padding:.32rem .7rem; border-radius:99px; white-space:nowrap;
          background:#FFF4E5; color:#9A5B00; border:1px solid #F5D9A8; }
.fuente.real { background:var(--verde-bg); color:var(--verde); border-color:#BFE3CB; }
.hoy { font-size:.72rem; color:var(--suave); background:var(--tarjeta); border:1px solid var(--borde);
       border-radius:99px; padding:.32rem .7rem; white-space:nowrap; }

/* --- Indicadores ----------------------------------------------------------- */
.kpis { display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:.8rem; margin-bottom:1.3rem; }
.kpi { background:var(--tarjeta); border:1px solid var(--borde); border-radius:14px; padding:.9rem 1rem;
       box-shadow:var(--sombra); display:flex; gap:.8rem; align-items:center; min-width:0; }
.kpi-ico { flex:0 0 40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center;
           background:var(--accion-suave); color:var(--accion); }
.kpi-ico svg { width:20px; height:20px; }
.kpi-t { color:var(--suave); font-size:.76rem; font-weight:500; }
.kpi-v { font-size:1.45rem; font-weight:800; color:var(--texto); line-height:1.2; letter-spacing:-.02em; }
.kpi-n { color:var(--suave); font-size:.72rem; }
.kpi.alerta .kpi-ico { background:var(--rojo-bg); color:var(--rojo); } .kpi.alerta .kpi-v { color:var(--rojo); }
.kpi.aviso .kpi-ico { background:var(--ambar-bg); color:var(--ambar); } .kpi.aviso .kpi-v { color:var(--ambar); }
.kpi.bien .kpi-ico { background:var(--verde-bg); color:var(--verde); }

/* --- Tablero --------------------------------------------------------------- */
.tablero-cab { display:flex; justify-content:space-between; align-items:center; color:var(--suave);
               font-size:.8rem; margin-bottom:.6rem; gap:1rem; flex-wrap:wrap; }
.tablero-cab b { color:var(--texto); font-size:1rem; font-weight:700; }
.tablero { display:grid; grid-template-columns:repeat(5, minmax(168px, 1fr)); gap:.7rem;
           overflow-x:auto; padding-bottom:.5rem; align-items:start; }
.columna { background:var(--panel); border-radius:16px; padding:.85rem .7rem 1rem; min-height:280px;
           border-top:3px solid var(--marino); }
.columna header { display:flex; justify-content:space-between; align-items:center; gap:.4rem; }
.columna h3 { font-size:.92rem; font-weight:700; margin:0; color:var(--texto); padding:0; }
.conteo { font-size:.75rem; font-weight:700; color:var(--marino); background:var(--tarjeta);
          border-radius:99px; min-width:24px; height:24px; display:flex; align-items:center; justify-content:center; padding:0 .45rem; }
.norma { display:inline-block; font-family:var(--mono); font-size:.68rem; font-weight:600; color:var(--marino);
         background:rgba(18,56,107,.08); border-radius:6px; padding:.14rem .45rem; margin:.45rem 0 .75rem; }
.tarjetas { display:flex; flex-direction:column; gap:.6rem; }
a.tarjeta, a.tarjeta:hover, a.tarjeta:visited { text-decoration:none; color:inherit; }
.tarjeta { display:block; background:var(--tarjeta); border:1px solid var(--borde); border-left:3px solid var(--gris-marca);
           border-radius:12px; padding:.75rem .8rem .7rem; box-shadow:var(--sombra);
           transition:border-color .15s, box-shadow .15s, transform .15s; }
.tarjeta.tono-rojo { border-left-color:var(--rojo); }
.tarjeta.tono-ambar { border-left-color:#E0A21B; }
.tarjeta.tono-azul { border-left-color:var(--accion); }
.tarjeta.tono-verde { border-left-color:#2E9E57; }
.tarjeta:hover { box-shadow:0 8px 20px rgba(16,24,40,.10); transform:translateY(-2px); }
.tarjeta.activa { box-shadow:0 0 0 3px rgba(31,95,175,.25); border-color:var(--accion); }
.codigo { font-family:var(--mono); font-size:.74rem; font-weight:600; color:var(--suave); }
.cliente { font-weight:700; font-size:.9rem; color:var(--texto); margin:.3rem 0 .25rem; line-height:1.3; }
.productos { color:var(--suave); font-size:.79rem; line-height:1.4; }
.barra { height:6px; background:#E9EDF3; border-radius:99px; overflow:hidden; margin:.6rem 0 .1rem; }
.barra span { display:block; height:100%; border-radius:99px; background:linear-gradient(90deg, var(--marino), var(--accion)); }
.barra.grande { height:8px; margin-top:1rem; }
.pie { display:flex; justify-content:space-between; align-items:center; gap:.4rem; flex-wrap:wrap; margin-top:.55rem; }
.chip { display:inline-block; font-size:.7rem; font-weight:600; border-radius:99px; padding:.2rem .6rem; }
.chip.rojo { background:var(--rojo-bg); color:var(--rojo); }
.chip.ambar { background:var(--ambar-bg); color:var(--ambar); }
.chip.azul { background:var(--azul-bg); color:var(--azul); }
.chip.verde { background:var(--verde-bg); color:var(--verde); }
.chip.gris { background:var(--gris-bg); color:var(--gris); }
.entrega { color:var(--suave); font-size:.72rem; white-space:nowrap; }
.vacio { color:var(--suave); font-size:.8rem; text-align:center; padding:1.4rem .5rem;
         border:1.5px dashed #CBD3DF; border-radius:12px; }

/* --- Detalle --------------------------------------------------------------- */
.caja { background:var(--tarjeta); border:1px solid var(--borde); border-radius:16px; box-shadow:var(--sombra); }
.detalle-cab { padding:1.3rem 1.5rem; margin-bottom:1rem; }
.detalle-cab h2 { margin:.25rem 0; font-size:1.35rem; font-weight:800; padding:0; color:var(--texto); }
.detalle-datos { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:.8rem; margin-top:1.1rem; }
.detalle-datos span { display:block; color:var(--suave); font-size:.74rem; margin-bottom:.15rem; }
.detalle-datos b { font-size:.92rem; color:var(--texto); }
.avance-t { color:var(--suave); font-size:.76rem; margin-top:.4rem; }
.stepper { display:grid; grid-template-columns:repeat(5, 1fr); padding:1.2rem .5rem; margin-bottom:1rem; }
.paso { text-align:center; position:relative; padding:0 .3rem; }
.paso:not(:last-child)::after { content:""; position:absolute; top:16px; left:calc(50% + 22px); right:calc(-50% + 22px);
                                height:2px; background:var(--borde); }
.paso.hecho:not(:last-child)::after { background:var(--marino); }
.bola { width:32px; height:32px; border-radius:50%; margin:0 auto .45rem; display:flex; align-items:center; justify-content:center;
        font-size:.8rem; font-weight:700; background:var(--gris-bg); color:var(--suave); }
.paso.hecho .bola { background:var(--marino); color:#fff; }
.paso.actual .bola { background:#fff; color:var(--accion); border:2px solid var(--accion); box-shadow:0 0 0 4px var(--accion-suave); }
.paso-n { font-size:.8rem; font-weight:600; color:var(--texto); }
.paso.pendiente .paso-n { color:var(--suave); }
.paso-r { font-family:var(--mono); font-size:.66rem; color:var(--suave); }
.subetapas { padding:.95rem 1.2rem; margin-bottom:1rem; }
.sub-t { font-weight:700; font-size:.88rem; margin-bottom:.5rem; color:var(--texto); }
.sub { display:inline-block; font-size:.76rem; padding:.25rem .7rem; border-radius:99px; margin:.15rem .3rem .15rem 0; }
.sub.hecho { background:var(--verde-bg); color:var(--verde); }
.sub.actual { background:var(--accion-suave); color:var(--accion); font-weight:700; }
.sub.pendiente { background:var(--gris-bg); color:var(--suave); }
.seccion-t { font-weight:700; font-size:1rem; color:var(--texto); margin:.4rem 0 .6rem; }
.timeline { list-style:none; margin:0; padding:.3rem 1.2rem; }
.timeline li { display:grid; grid-template-columns:140px 1fr; gap:1rem; padding:.8rem 0; border-bottom:1px solid var(--borde); }
.timeline li:last-child { border-bottom:none; }
.t-fecha { font-size:.74rem; color:var(--suave); padding-top:.45rem; }
.t-cuerpo .norma { margin:0 0 .3rem; }
.t-desc { font-size:.88rem; color:var(--texto); }
.t-pie { color:var(--suave); font-size:.76rem; margin-top:.2rem; }
.evidencia { margin-left:.5rem; color:var(--accion); }
.volver { margin-bottom:.6rem; }
.volver a { color:var(--accion); text-decoration:none; font-weight:600; font-size:.85rem; }

/* --- Barra lateral: rail azul marino, como el Control Center ---------------- */
[data-testid="stSidebar"] { background: linear-gradient(180deg, var(--marino-900) 0%, #0A1F3D 100%); border-right:none; }
[data-testid="stSidebarHeader"] { height:2.2rem; min-height:0; padding:.4rem .6rem 0; }
[data-testid="stSidebarUserContent"] { padding-top:0; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.4rem; }
.logo-caja { background:#fff; border-radius:16px; padding:.85rem; display:grid; place-items:center;
             box-shadow:0 6px 18px rgba(0,0,0,.25); }
.logo-caja img { height:74px; width:auto; display:block; }
.app-nombre { text-align:center; margin:.6rem 0 .2rem; }
.app-nombre b { display:block; color:#fff; font-size:.98rem; font-weight:700; letter-spacing:.01em; }
.app-nombre span { color:#93A4BF; font-size:.72rem; }
.rail-etiqueta { color:#7F93B3; font-size:.68rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
                 margin:0 0 0 .2rem; }
.cuenta { display:flex; gap:.7rem; align-items:center; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.09);
          border-radius:14px; padding:.65rem .75rem; margin-top:.4rem; }
.avatar { flex:0 0 36px; height:36px; border-radius:50%; background:linear-gradient(135deg, #1F5FAF, #4C8BD8);
          color:#fff; font-weight:700; font-size:.82rem; display:flex; align-items:center; justify-content:center; }
.cuenta b { display:block; color:#fff; font-size:.83rem; line-height:1.25; }
.cuenta span { color:#93A4BF; font-size:.72rem; }
[data-testid="stSidebar"] label p { color:#93A4BF !important; font-size:.75rem; font-weight:600; }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] .react-aria-ComboBox, [data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] {
  background:rgba(255,255,255,.07) !important; border-color:rgba(255,255,255,.16) !important; border-radius:10px; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] * { color:#E8EEF7 !important; }
[data-testid="stSidebar"] .react-aria-ComboBox > div { background:transparent !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.rail-etiqueta),
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.rail-pie),
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.app-nombre) { margin-bottom:0 !important; }
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.rail-etiqueta) { margin-top:.6rem; }
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.rail-pie) { margin-top:1rem; margin-bottom:.4rem; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] svg { fill:#93A4BF !important; }

/* Lista desplegable del selector de cliente */
div[role="listbox"] [role="option"], ul[role="listbox"] li { font-size:.88rem !important; }
.cliente-sel { color:#93A4BF; font-size:.72rem; margin:-.1rem 0 0 .2rem; }

/* Barra de herramientas del tablero */
div.st-key-herramientas [data-testid="stHorizontalBlock"] { align-items:center; }
div.st-key-herramientas [data-testid="stPopover"] button, div[class*="st-key-descarga"] button {
  border-radius:10px; font-weight:600; }

/* Menú: botones planos, la pantalla actual en píldora azul */
[data-testid="stSidebar"] div[class*="st-key-nav_"] button {
  justify-content:flex-start; width:100%; min-height:44px; border-radius:11px; border:none; padding:0 .85rem;
  background:transparent; box-shadow:none; transition:background .15s; }
[data-testid="stSidebar"] div[class*="st-key-nav_"] button * { color:#C9D4E5 !important; }
[data-testid="stSidebar"] div[class*="st-key-nav_"] button p { font-size:.9rem; font-weight:500; }
[data-testid="stSidebar"] div[class*="st-key-nav_"] button > div,
[data-testid="stSidebar"] div[class*="st-key-nav_"] button span { justify-content:flex-start; }
[data-testid="stSidebar"] div[class*="st-key-nav_"] button:hover { background:rgba(255,255,255,.07); }
[data-testid="stSidebar"] div[class*="st-key-nav_"] [data-testid="stBaseButton-primary"] {
  background:linear-gradient(90deg, #1F5FAF, #2B6FC2); box-shadow:0 6px 16px rgba(31,95,175,.35); }
[data-testid="stSidebar"] div[class*="st-key-nav_"] [data-testid="stBaseButton-primary"] * { color:#fff !important; font-weight:600; }
.rail-pie { padding-top:.9rem; border-top:1px solid rgba(255,255,255,.09);
            color:#93A4BF; font-size:.74rem; display:flex; align-items:center; gap:.5rem; }
.punto { width:8px; height:8px; border-radius:50%; background:#F5B547; box-shadow:0 0 0 3px rgba(245,181,71,.2); flex:0 0 8px; }
.punto.real { background:#3CCB7F; box-shadow:0 0 0 3px rgba(60,203,127,.2); }
[data-testid="stSidebar"] div.st-key-actualizar button { background:transparent; border:1px solid rgba(255,255,255,.18);
  border-radius:10px; min-height:38px; }
[data-testid="stSidebar"] div.st-key-actualizar button * { color:#C9D4E5 !important; font-size:.82rem; }
[data-testid="stSidebar"] div.st-key-actualizar button:hover { background:rgba(255,255,255,.07); }
[data-testid="stSidebarCollapseButton"] * { color:#93A4BF !important; }

/* Solo en el teléfono: accesos rápidos a cada etapa */
.etapas-nav { display:none; }

/* --- Teléfono -------------------------------------------------------------- */
@media (max-width: 1100px) { .kpis { grid-template-columns:repeat(3, minmax(0,1fr)); } }
@media (max-width: 900px) {
  .kpis { grid-template-columns:repeat(2, minmax(0,1fr)); }
  .detalle-datos { grid-template-columns:repeat(2, minmax(0,1fr)); }
}
@media (max-width: 640px) {
  .block-container { padding-left:1rem; padding-right:1rem; padding-top:3.2rem; }
  [data-testid="stHeader"] { background:var(--fondo); }
  .titulo h1 { font-size:1.35rem; }
  .titulo-der .hoy { display:none; }
  /* Indicadores: una tira que se desliza, no cinco tarjetas apiladas */
  .kpis { display:flex; overflow-x:auto; scroll-snap-type:x mandatory; gap:.6rem; margin:0 -1rem 1rem;
          padding:0 1rem .3rem; scrollbar-width:none; }
  .kpis::-webkit-scrollbar { display:none; }
  .kpi { flex:0 0 66%; scroll-snap-align:start; padding:.75rem .85rem; }
  .kpi-ico { flex:0 0 34px; height:34px; }
  .kpi-v { font-size:1.3rem; }
  /* Tablero: etapas una debajo de otra; la barra de accesos queda fija arriba */
  .tablero-cab span { display:none; }
  .etapas-nav { display:flex; gap:.45rem; overflow-x:auto; margin:0 -1rem .7rem; padding:.5rem 1rem;
                scrollbar-width:none; position:sticky; top:2.9rem; z-index:5; background:var(--fondo); }
  .etapas-nav::-webkit-scrollbar { display:none; }
  .etapas-nav a { flex:0 0 auto; text-decoration:none; color:var(--marino); background:var(--tarjeta);
                  border:1px solid var(--borde); border-radius:99px; padding:.45rem .8rem; font-size:.8rem;
                  font-weight:600; box-shadow:var(--sombra); min-height:40px; display:flex; align-items:center; gap:.4rem; }
  .etapas-nav a b { background:var(--marino); color:#fff; border-radius:99px; font-size:.7rem; padding:.05rem .45rem; }
  .tablero { grid-template-columns:1fr; overflow-x:visible; gap:.9rem; }
  .columna { min-height:0; scroll-margin-top:7rem; }
  .columna .vacio { padding:.8rem; }
  .tarjeta { padding:.9rem .95rem .85rem; }
  .tarjeta:hover { transform:none; }
  .cliente { font-size:.98rem; }
  .stepper { grid-template-columns:1fr; gap:.6rem; text-align:left; padding:1rem; }
  .paso { display:grid; grid-template-columns:40px 1fr; text-align:left; align-items:center; }
  .paso .bola { margin:0; grid-row:span 2; }
  .paso:not(:last-child)::after { display:none; }
  .timeline li { grid-template-columns:1fr; gap:.2rem; }
  .t-fecha { padding-top:0; }
}
</style>
"""
