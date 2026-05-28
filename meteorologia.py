import requests
import pandas as pd
import airportsdata
import io

def obtener_iata(icao_code):
    try:
        airports = airportsdata.load('ICAO')
        if icao_code in airports:
            iata = airports[icao_code]['iata']
            return iata if iata else "NO_IATA"
        return "DESCONOCIDO"
    except:
        return "ERROR"

def procesar_meteorologia(station, fecha_inicio, fecha_fin, lista_variables):
    """
    Construye la matriz dinámica mensual, calcula el promedio de las variables,
    fuerza a que todos los datos de temperatura (tmpc) sean números enteros
    y organiza las columnas de totales al lado izquierdo.
    """
    try:
        # 1. Mapeo técnico de variables
        mapeo_iem = {
            "QNH": "alti",
            "Temperatura": "tmpc",
            "Viento": "sknt",
            "Humedad": "relh",
            "Visibilidad": "vsby"
        }
        
        y1, m1, d1 = fecha_inicio.year, fecha_inicio.month, fecha_inicio.day
        y2, m2, d2 = fecha_fin.year, fecha_fin.month, fecha_fin.day
        
        campos_datos = [f"data={mapeo_iem[v]}" for v in lista_variables if v in mapeo_iem]
        string_datos = "&".join(campos_datos)
        
        url = (f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?"
               f"station={station}&{string_datos}&year1={y1}&month1={m1}&day1={d1}&"
               f"year2={y2}&month2={m2}&day2={d2}&tz=Etc%2FUTC&format=comma&direct=yes&report_type=3")
        
        r = requests.get(url)
        if r.status_code != 200:
            return None, "Error en el servidor de IEM ASOS"
            
        lineas = r.text.splitlines()
        datos_limpios = [l for l in lineas if not l.startswith("#")]
        
        if len(datos_limpios) <= 1:
            return None, "No se encontraron registros meteorológicos."
            
        # 2. Cargar datos en el DataFrame
        df = pd.read_csv(io.StringIO("\n".join(datos_limpios)))
        df['valid'] = pd.to_datetime(df['valid'])
        
        columnas_tecnicas = [mapeo_iem[v] for v in lista_variables if v in mapeo_iem]
        for col in columnas_tecnicas:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # 3. Formatear componentes de Tiempo
        df['Etiquetas de fila'] = df['valid'].dt.strftime('%I %p')
        df['Mes'] = df['valid'].dt.strftime('%b')
        
        meses_ordenados = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        meses_en_datos = [m for m in meses_ordenados if m in df['Mes'].unique()]
        df['Mes'] = pd.Categorical(df['Mes'], categories=meses_en_datos, ordered=True)
        
        horas_ordenadas = pd.date_range("00:00", "23:00", freq="h").strftime('%I %p').tolist()
        df['Etiquetas de fila'] = pd.Categorical(df['Etiquetas de fila'], categories=horas_ordenadas, ordered=True)

        # 4. Pivotar la tabla (Genera columnas tipo: Apr_alti, Apr_tmpc...)
        df_pivot = df.pivot_table(
            values=columnas_tecnicas,
            index='Etiquetas de fila',
            columns='Mes',
            aggfunc='mean',
            observed=False
        ).round(2)
        
        # Aplanar los encabezados superiores
        df_pivot.columns = [f"{mes}_{var}" for var, mes in df_pivot.columns]
        df_pivot = df_pivot.reset_index()
        
        # --- 5. CÁLCULO DE TOTALES HORIZONTALES REALES ---
        totales_columnas = []
        
        # Buscar y procesar columnas de temperatura
        cols_tmpc = [c for c in df_pivot.columns if '_tmpc' in c]
        if cols_tmpc:
            nombre_total_tmpc = "Total Promedio de tmpc"
            df_pivot[nombre_total_tmpc] = df_pivot[cols_tmpc].mean(axis=1).round(2)
            totales_columnas.append(nombre_total_tmpc)
            
        # Buscar y procesar columnas de QNH
        cols_alti = [c for c in df_pivot.columns if '_alti' in c]
        if cols_alti and "QNH" in lista_variables:
            nombre_total_alti = "Total Promedio de alti"
            df_pivot[nombre_total_alti] = df_pivot[cols_alti].mean(axis=1).round(2)
            totales_columnas.append(nombre_total_alti)
        
        # --- 6. CONVERSIÓN ESTRICTA DE TEMPERATURAS A NÚMEROS ENTEROS ---
        # Identificamos todas las columnas de temperatura presentes (incluyendo la de Total)
        todas_las_cols_tmpc = cols_tmpc + ([nombre_total_tmpc] if cols_tmpc else [])
        
        for col_t in todas_las_cols_tmpc:
            if col_t in df_pivot.columns:
                # Redondeamos y transformamos a tipo entero de Pandas que acepta nulos (Int64)
                df_pivot[col_t] = df_pivot[col_t].round(0).astype("Int64")
        
        # --- 7. REORDENACIÓN DE COLUMNAS (Totales al principio izquierdo fijo) ---
        columnas_meses = [c for c in df_pivot.columns if c != 'Etiquetas de fila' and c not in totales_columnas]
        orden_final_columnas = ['Etiquetas de fila'] + totales_columnas + columnas_meses
        
        df_final = df_pivot[orden_final_columnas]
        
        return df_final, "Éxito"
        
    except Exception as e:
        return None, str(e)