"""Hoja de estilos de la app. Texto plano (NO f-string): las llaves van simples."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
  --fondo: #F5F1EA;
  --panel: #EDE7DC;
  --tarjeta: #FFFFFF;
  --borde: #E2D9CB;
  --texto: #2B2520;
  --suave: #7A6F63;
  --acento: #C2601E;
  --acento-suave: #F6E3D5;
  --rojo-bg: #F6D9D2; --rojo: #9B2C1F;
  --ambar-bg: #F7EAC0; --ambar: #8A5A00;
  --azul-bg: #DCE6F7; --azul: #1F4E99;
  --verde-bg: #DCEFD9; --verde: #2E6B2A;
  --gris-bg: #ECE7DF; --gris: #5B5348;
  --mono: 'JetBrains Mono', ui-monospace, Menlo, monospace;
}

html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', system-ui, sans-serif; }
[data-testid="stAppViewContainer"] { background: var(--fondo); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1500px; }

/* --- Encabezado ------------------------------------------------------------ */
.titulo { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-bottom:1rem; }
.titulo h1 { font-size:1.65rem; font-weight:700; margin:0; color:var(--texto); }
.titulo p { margin:.15rem 0 0; color:var(--suave); font-size:.92rem; }
.fuente { font-family:var(--mono); font-size:.75rem; padding:.3rem .6rem; border-radius:6px;
          background:var(--acento-suave); color:var(--acento); border:1px solid #EBC7AD; white-space:nowrap; }
.fuente.real { background:var(--verde-bg); color:var(--verde); border-color:#BFDDB9; }

/* --- Indicadores ----------------------------------------------------------- */
.kpis { display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:.75rem; margin-bottom:1.25rem; }
.kpi { background:var(--tarjeta); border:1px solid var(--borde); border-radius:12px; padding:.8rem 1rem; }
.kpi-t { color:var(--suave); font-size:.78rem; font-weight:500; }
.kpi-v { font-size:1.5rem; font-weight:700; color:var(--texto); line-height:1.3; }
.kpi-n { color:var(--suave); font-size:.74rem; font-family:var(--mono); }
.kpi.alerta { border-color:#E9B5A9; } .kpi.alerta .kpi-v { color:var(--rojo); }
.kpi.aviso { border-color:#E8D18C; } .kpi.aviso .kpi-v { color:var(--ambar); }

/* --- Tablero --------------------------------------------------------------- */
.tablero-cab { text-align:right; color:var(--suave); font-size:.85rem; margin-bottom:.5rem; }
.tablero { display:grid; grid-template-columns:repeat(5, minmax(180px, 1fr)); gap:.75rem;
           overflow-x:auto; padding-bottom:.5rem; align-items:start; }
.columna { background:var(--panel); border:1px solid var(--borde); border-radius:14px; padding:.9rem .8rem 1rem; min-height:420px; }
.columna header { display:flex; justify-content:space-between; align-items:center; }
.columna h3 { font-size:1rem; font-weight:700; margin:0; color:var(--texto); padding:0; }
.conteo { font-family:var(--mono); font-size:.85rem; color:var(--suave); }
.norma { display:inline-block; font-family:var(--mono); font-size:.72rem; font-weight:600; color:#4C5D78;
         background:#E3E7EE; border-radius:5px; padding:.15rem .45rem; margin:.45rem 0 .7rem; }
.tarjetas { display:flex; flex-direction:column; gap:.7rem; }
a.tarjeta, a.tarjeta:hover, a.tarjeta:visited { text-decoration:none; color:inherit; }
.tarjeta { display:block; background:var(--tarjeta); border:1px solid var(--borde); border-radius:10px;
           padding:.8rem .85rem .75rem; transition:border-color .15s, box-shadow .15s, transform .15s; }
.tarjeta:hover { border-color:var(--acento); box-shadow:0 4px 14px rgba(120,70,20,.10); transform:translateY(-1px); }
.tarjeta.activa { border:1.5px solid var(--acento); box-shadow:0 0 0 3px var(--acento-suave); }
.codigo { font-family:var(--mono); font-size:.8rem; font-weight:600; color:#3D3530; letter-spacing:.01em; }
.cliente { font-weight:700; font-size:.95rem; color:var(--texto); margin:.35rem 0 .3rem; line-height:1.3; }
.productos { color:var(--suave); font-size:.82rem; line-height:1.4; }
.barra { height:5px; background:#ECE6DC; border-radius:99px; overflow:hidden; margin:.6rem 0 .1rem; }
.barra span { display:block; height:100%; background:var(--acento); border-radius:99px; }
.barra.grande { height:8px; margin-top:1rem; }
.chip { display:inline-block; font-size:.76rem; font-weight:600; border-radius:99px; padding:.22rem .7rem; margin-top:.55rem; }
.chip.rojo { background:var(--rojo-bg); color:var(--rojo); }
.chip.ambar { background:var(--ambar-bg); color:var(--ambar); }
.chip.azul { background:var(--azul-bg); color:var(--azul); }
.chip.verde { background:var(--verde-bg); color:var(--verde); }
.chip.gris { background:var(--gris-bg); color:var(--gris); }
.entrega { color:var(--suave); font-size:.8rem; margin-top:.5rem; }
.vacio { color:var(--suave); font-size:.82rem; text-align:center; padding:1.5rem .5rem;
         border:1px dashed var(--borde); border-radius:10px; }

/* --- Detalle --------------------------------------------------------------- */
.detalle-cab { background:var(--tarjeta); border:1px solid var(--borde); border-radius:14px; padding:1.2rem 1.4rem; margin-bottom:1rem; }
.detalle-cab h2 { margin:.2rem 0; font-size:1.4rem; font-weight:700; padding:0; }
.detalle-datos { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:.8rem; margin-top:1rem; }
.detalle-datos span { display:block; color:var(--suave); font-size:.75rem; }
.detalle-datos b { font-size:.92rem; }
.detalle-datos b.chip { margin-top:.15rem; }
.avance-t { color:var(--suave); font-size:.78rem; margin-top:.35rem; font-family:var(--mono); }
.stepper { display:grid; grid-template-columns:repeat(5, 1fr); background:var(--tarjeta); border:1px solid var(--borde);
           border-radius:14px; padding:1.1rem .5rem; margin-bottom:1rem; }
.paso { text-align:center; position:relative; padding:0 .3rem; }
.paso:not(:last-child)::after { content:""; position:absolute; top:15px; left:calc(50% + 20px); right:calc(-50% + 20px);
                                height:2px; background:var(--borde); }
.paso.hecho:not(:last-child)::after { background:var(--acento); }
.bola { width:30px; height:30px; border-radius:50%; margin:0 auto .4rem; display:flex; align-items:center; justify-content:center;
        font-size:.82rem; font-weight:700; background:var(--gris-bg); color:var(--suave); }
.paso.hecho .bola { background:var(--acento); color:#fff; }
.paso.actual .bola { background:#fff; color:var(--acento); border:2px solid var(--acento); box-shadow:0 0 0 4px var(--acento-suave); }
.paso-n { font-size:.82rem; font-weight:600; }
.paso.pendiente .paso-n { color:var(--suave); }
.paso-r { font-family:var(--mono); font-size:.68rem; color:var(--suave); }
.subetapas { background:var(--tarjeta); border:1px solid var(--borde); border-radius:14px; padding:.9rem 1.1rem; margin-bottom:1rem; }
.sub-t { font-weight:700; font-size:.9rem; margin-bottom:.5rem; }
.sub { display:inline-block; font-size:.78rem; padding:.25rem .7rem; border-radius:99px; margin:.15rem .3rem .15rem 0; }
.sub.hecho { background:var(--verde-bg); color:var(--verde); }
.sub.actual { background:var(--acento-suave); color:var(--acento); font-weight:700; }
.sub.pendiente { background:var(--gris-bg); color:var(--suave); }
.timeline { list-style:none; margin:0; padding:0; }
.timeline li { display:grid; grid-template-columns:150px 1fr; gap:1rem; padding:.75rem 0; border-bottom:1px solid var(--borde); }
.timeline li:last-child { border-bottom:none; }
.t-fecha { font-family:var(--mono); font-size:.75rem; color:var(--suave); padding-top:.5rem; }
.t-cuerpo .norma { margin:0 0 .3rem; }
.t-desc { font-size:.9rem; }
.t-pie { color:var(--suave); font-size:.78rem; margin-top:.2rem; }
.evidencia { margin-left:.5rem; color:#4C5D78; }
.volver a { color:var(--acento); text-decoration:none; font-weight:600; font-size:.9rem; }

/* --- Barra lateral --------------------------------------------------------- */
[data-testid="stSidebar"] { background:#2B2520; }
[data-testid="stSidebar"] * { color:#EDE7DC; }
[data-testid="stSidebar"] [data-baseweb="select"] *, [data-testid="stSidebar"] .react-aria-ComboBox * { color:var(--texto); }
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] { background:#C2601E; border:none; }
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] p { color:#fff !important; font-weight:600; }
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover { background:#A9511A; }
.marca { font-weight:700; font-size:1.25rem; letter-spacing:.02em; }
.marca span { color:#E8915A; }
.marca-sub { font-family:var(--mono); font-size:.72rem; color:#B9AC9C !important; margin-bottom:1rem; }

/* --- Teléfono -------------------------------------------------------------- */
@media (max-width: 900px) {
  .kpis { grid-template-columns:repeat(2, minmax(0,1fr)); }
  .detalle-datos { grid-template-columns:repeat(2, minmax(0,1fr)); }
}
@media (max-width: 640px) {
  .block-container { padding-left:1rem; padding-right:1rem; }
  .tablero { grid-template-columns:1fr; overflow-x:visible; }
  .columna { min-height:0; }
  .stepper { grid-template-columns:1fr; gap:.6rem; text-align:left; }
  .paso { display:grid; grid-template-columns:36px 1fr; text-align:left; align-items:center; }
  .paso .bola { margin:0; grid-row:span 2; }
  .paso:not(:last-child)::after { display:none; }
  .timeline li { grid-template-columns:1fr; gap:.2rem; }
  .t-fecha { padding-top:0; }
}
</style>
"""
