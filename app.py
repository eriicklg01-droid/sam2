import streamlit as st
import meteorologia
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.colors as mcolors

st.set_page_config(page_title="SAM Online FREE XXXX", layout="wide")

st.title("SAM 2.0")
st.subheader("Matriz")
st.markdown("---")

with st.sidebar:
    st.header("Parámetros")
    estacion = st.text_input("Código ICAO", value="", max_chars=4).upper()
    
    variables_seleccionadas = st.multiselect(
        "Variables",
        ["QNH", "Temperatura", "Viento", "Humedad", "Visibilidad"],
        default=["QNH", "Temperatura"]
    )
    
    st.subheader("Rango de Fechas")
    fecha_inicio = st.date_input("Desde:", datetime(2021, 3, 1))
    fecha_fin = st.date_input("Hasta:", datetime(2026, 3, 1))
    
    btn_ejecutar = st.button("Generar Tabla", use_container_width=True)

if btn_ejecutar:
    if not variables_seleccionadas:
        st.error("Seleccione al menos una variable.")
    else:
        with st.spinner("Construyendo matriz y aplicando formato"):
            
            df_matriz, status = meteorologia.procesar_meteorologia(
                estacion, fecha_inicio, fecha_fin, variables_seleccionadas
            )
            
            if df_matriz is not None:
                st.success("¡Reporte generado de manera exitosa!")
                
                st.session_state['df_matriz_original'] = df_matriz
                st.session_state['estacion_actual'] = estacion
            else:
                st.error(f"Error: {status}")

if 'df_matriz_original' in st.session_state:
    df_origen = st.session_state['df_matriz_original']
    estacion_act = st.session_state['estacion_actual']
    iata_code = meteorologia.obtener_iata(estacion_act)
    
    st.markdown("---")
    st.subheader(f"🔍 Filtrar Visualización (Datos Disponibles)")
    
    lista_meses_fijos = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    meses_disponibles = sorted(list(set([col.split('_')[0] for col in df_origen.columns if col.split('_')[0] in lista_meses_fijos])), 
                               key=lambda x: lista_meses_fijos.index(x))
    
    meses_filtrados = st.multiselect(
        "Selecciona los meses que deseas filtrar:",
        options=meses_disponibles
    )
    
    columnas_a_mostrar = ['Etiquetas de fila']
    
    if "Total Promedio de tmpc" in df_origen.columns:
        columnas_a_mostrar.append("Total Promedio de tmpc")
    if "Total Promedio de alti" in df_origen.columns:
        columnas_a_mostrar.append("Total Promedio de alti")
        
    for col in df_origen.columns:
        if col not in columnas_a_mostrar:
            if meses_filtrados:
                if any(col.startswith(f"{mes}_") for mes in meses_filtrados):
                    columnas_a_mostrar.append(col)
            else:
                # Si no hay filtro, se agregan todas de forma normal
                columnas_a_mostrar.append(col)
                
    df_filtrado = df_origen[columnas_a_mostrar]
    
    st.subheader(f"Datos: TD- {estacion_act} ({iata_code})")
    
    formatos_columnas = {}
    for col in df_filtrado.columns:
        if col == 'Etiquetas de fila':
            continue
        elif 'tmpc' in col:
            formatos_columnas[col] = "{:.0f}"
        else:
            formatos_columnas[col] = "{:.2f}"
    
    df_style = df_filtrado.style.format(formatos_columnas, na_rep="-")

    if "Total Promedio de tmpc" in df_filtrado.columns:
        cmap_tricolor = mcolors.LinearSegmentedColormap.from_list(
            "azul_blanco_rojo", 
            ["#1f77b4", "#ffffff", "#d62728"]
        )
        
        df_style = df_style.background_gradient(
            cmap=cmap_tricolor,
            subset=["Total Promedio de tmpc"],
            text_color_threshold=0.4  
        )
    
    st.dataframe(df_style, use_container_width=True, hide_index=True)
    
    csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar en CSV (Vista Actual)",
        data=csv_data,
        file_name=f"TD_DATOS_FILTRADOS_{estacion_act}.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("Configure los parámetros y presione el botón para construir la matriz.")