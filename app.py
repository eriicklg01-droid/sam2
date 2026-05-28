import streamlit as st
import meteorologia
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.colors as mcolors
import io

st.set_page_config(page_title="SAM Online", layout="wide")

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
    st.subheader(f"Filtrar Visualización (Datos Disponibles)")
    
    lista_meses_fijos = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    meses_disponibles = sorted(list(set([col.split('_')[0] for col in df_origen.columns if col.split('_')[0] in lista_meses_fijos])), 
                               key=lambda x: lista_meses_fijos.index(x))
    
    meses_filtrados = st.multiselect(
        "Selecciona los meses que deseas visualizar (Deja vacío para ver todos):",
        options=meses_disponibles
    )
    
    columnas_meses_visibles = []
    for col in df_origen.columns:
        if col != 'Etiquetas de fila':
            if meses_filtrados:
                if any(col.startswith(f"{mes}_") for mes in meses_filtrados):
                    columnas_meses_visibles.append(col)
            else:
                columnas_meses_visibles.append(col)
                
    df_filtrado = df_origen[['Etiquetas de fila'] + columnas_meses_visibles].copy()
    
    totales_columnas_dinamicas = []
    
    cols_tmpc_visibles = [c for c in columnas_meses_visibles if '_tmpc' in c]
    if cols_tmpc_visibles:
        nombre_total_tmpc = "Total Promedio de tmpc"
        df_filtrado[nombre_total_tmpc] = df_filtrado[cols_tmpc_visibles].mean(axis=1).round(0).astype("Int64")
        totales_columnas_dinamicas.append(nombre_total_tmpc)
        
    cols_alti_visibles = [c for c in columnas_meses_visibles if '_alti' in c]
    if cols_alti_visibles:
        nombre_total_alti = "Total Promedio de alti"
        df_filtrado[nombre_total_alti] = df_filtrado[cols_alti_visibles].mean(axis=1).round(2)
        totales_columnas_dinamicas.append(nombre_total_alti)
        
    # 4. Reordenar de izquierda a derecha fijos: Horas -> Totales Dinámicos -> Meses
    orden_columnas = ['Etiquetas de fila'] + totales_columnas_dinamicas + columnas_meses_visibles
    df_filtrado = df_filtrado[orden_columnas]
    
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
    
    st.markdown("---")
    st.subheader(f"Ubicación Geográfica de la Estación - {estacion_act}")
    df_mapa = meteorologia.obtener_coordenadas(estacion_act)
    if df_mapa is not None:
        st.map(df_mapa, zoom=12, use_container_width=True)
    else:
        st.warning("Coordenadas no disponibles para el mapa.")
    
    st.markdown("---")
    
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, sheet_name='TD_DATOS', index=False)
    data_excel = buffer_excel.getvalue()
    
    st.download_button(
        label="Descargar Matriz",
        data=data_excel,
        file_name=f"TD_DATOS_DINAMICOS_{estacion_act}.xlsm",
        mime="application/vnd.ms-excel.sheet.macroEnabled.12",
        use_container_width=True
    )
else:
    st.info("Configure los parámetros y presione el botón para construir la matriz.")
