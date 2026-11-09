"""Panel interactivo para el CSV de ventas de Programación 2."""
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Análisis de ventas | Programación 2", page_icon="📊", layout="wide")

@st.cache_data(show_spinner=False)
def leer_ventas(contenido: bytes) -> pd.DataFrame:
    """Carga CSV con delimitadores comunes; valida campos y tipos esperados."""
    error = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(contenido), sep=None, engine="python", encoding=encoding)
            break
        except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
            error = e
    else:
        raise ValueError(f"No fue posible leer el CSV: {error}")
    df.columns = df.columns.astype(str).str.strip().str.lower()
    necesarias = {"fecha", "color", "unidades"}
    if not necesarias.issubset(df.columns):
        raise ValueError("El archivo debe contener las columnas: fecha, color y unidades.")
    df = df[["fecha", "color", "unidades"]].copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["color"] = df["color"].astype("string").str.strip()
    df["unidades"] = pd.to_numeric(df["unidades"], errors="coerce")
    df = df.dropna(subset=["fecha", "color", "unidades"])
    if df.empty:
        raise ValueError("No se encontraron registros válidos en el CSV.")
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    df["año"] = df["fecha"].dt.year
    return df

st.title("📊 Panel interactivo de ventas")
st.caption("Control de Programación 2 · Streamlit, Pandas y Plotly")
st.write("Explora las unidades vendidas por mes y color. Filtra los resultados, observa gráficos interactivos y descarga la tabla.")

st.sidebar.header("Datos de ventas")
archivo = st.sidebar.file_uploader("Cargar otro CSV (opcional)", type=["csv"])
try:
    if archivo is not None:
        datos = leer_ventas(archivo.getvalue())
        st.sidebar.success(f"Archivo cargado: {archivo.name}")
    else:
        ruta = Path(__file__).with_name("ventas.csv")
        if not ruta.exists():
            st.error("No se encontró ventas.csv. Súbelo junto a app.py en GitHub o usa el cargador de la izquierda.")
            st.stop()
        datos = leer_ventas(ruta.read_bytes())
        st.sidebar.success("Usando ventas.csv del proyecto")
except (ValueError, OSError) as exc:
    st.error(f"No se pudo procesar el archivo: {exc}")
    st.stop()

st.sidebar.header("Filtros interactivos")
años = sorted(datos["año"].unique().tolist())
seleccion_años = st.sidebar.multiselect("Años", años, default=años)
colores = sorted(datos["color"].dropna().unique().tolist())
seleccion_colores = st.sidebar.multiselect("Colores", colores, default=colores)
filtrado = datos.loc[datos["año"].isin(seleccion_años) & datos["color"].isin(seleccion_colores)].copy()

if filtrado.empty:
    st.warning("No hay datos para los filtros seleccionados. Marca al menos un año y un color.")
    st.stop()

primera, segunda, tercera, cuarta = st.columns(4)
primera.metric("Unidades vendidas", f"{int(filtrado['unidades'].sum()):,}".replace(",", "."))
segunda.metric("Registros", len(filtrado))
tercera.metric("Colores seleccionados", filtrado["color"].nunique())
cuarta.metric("Meses con ventas", filtrado["mes"].nunique())

mensual = filtrado.groupby(["mes", "color"], as_index=False)["unidades"].sum()
resumen_color = filtrado.groupby("color", as_index=False)["unidades"].sum().sort_values("unidades", ascending=False)

st.subheader("Evolución mensual de unidades vendidas")
tipo = st.radio("Visualización", ["Líneas", "Barras"], horizontal=True)
if tipo == "Líneas":
    fig = px.line(mensual, x="mes", y="unidades", color="color", markers=True, labels={"mes": "Mes", "unidades": "Unidades", "color": "Color"})
else:
    fig = px.bar(mensual, x="mes", y="unidades", color="color", barmode="group", labels={"mes": "Mes", "unidades": "Unidades", "color": "Color"})
fig.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

izq, der = st.columns(2)
with izq:
    st.subheader("Unidades por color")
    st.plotly_chart(px.bar(resumen_color, x="color", y="unidades", color="color", labels={"color": "Color", "unidades": "Unidades"}), use_container_width=True)
with der:
    st.subheader("Participación por color")
    st.plotly_chart(px.pie(resumen_color, names="color", values="unidades", hole=0.35), use_container_width=True)

st.subheader("Análisis estadístico")
resumen = filtrado.groupby("color")["unidades"].agg(["count", "sum", "mean", "min", "max"]).rename(columns={"count": "Registros", "sum": "Total", "mean": "Promedio", "min": "Mínimo", "max": "Máximo"})
st.dataframe(resumen.round(2), use_container_width=True)

st.subheader("Registros filtrados")
tabla = filtrado[["fecha", "color", "unidades"]].sort_values(["fecha", "color"])
st.dataframe(tabla, use_container_width=True, hide_index=True)
st.download_button("⬇️ Descargar registros filtrados", data=tabla.to_csv(index=False, sep=";").encode("utf-8-sig"), file_name="ventas_filtradas.csv", mime="text/csv")
st.caption("Los datos representan cantidades de unidades, no valores monetarios. Fuente: ventas.csv.")
