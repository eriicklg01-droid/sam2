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
    try:
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
            
        df = pd.read_csv(io.StringIO("\n".join(datos_limpios)))
        df['valid'] = pd.to_datetime(df['valid'])
        
        columnas_tecnicas = [mapeo_iem[v] for v in lista_variables if v in mapeo_iem]
        for col in columnas_tecnicas:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df['Etiquetas de fila'] = df['valid'].dt.strftime('%I %p')
        df['Mes'] = df['valid'].dt.strftime('%b')
        
        meses_ordenados = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        meses_en_datos = [m for m in meses_ordenados if m in df['Mes'].unique()]
        df['Mes'] = pd.Categorical(df['Mes'], categories=meses_en_datos, ordered=True)
        
        horas_ordenadas = pd.date_range("00:00", "23:00", freq="h").strftime('%I %p').tolist()
        df['Etiquetas de fila'] = pd.Categorical(df['Etiquetas de fila'], categories=horas_ordenadas, ordered=True)

        df_pivot = df.pivot_table(
            values=columnas_tecnicas,
            index='Etiquetas de fila',
            columns='Mes',
            aggfunc='mean',
            observed=False
        ).round(2)
        
        df_pivot.columns = [f"{mes}_{var}" for var, mes in df_pivot.columns]
        df_pivot = df_pivot.reset_index()
        
        totales_columnas = []
        
        cols_tmpc = [c for c in df_pivot.columns if '_tmpc' in c]
        if cols_tmpc:
            nombre_total_tmpc = "Total Promedio de tmpc"
            df_pivot[nombre_total_tmpc] = df_pivot[cols_tmpc].mean(axis=1).round(2)
            totales_columnas.append(nombre_total_tmpc)
            
        cols_alti = [c for c in df_pivot.columns if '_alti' in c]
        if cols_alti and "QNH" in lista_variables:
            nombre_total_alti = "Total Promedio de alti"
            df_pivot[nombre_total_alti] = df_pivot[cols_alti].mean(axis=1).round(2)
            totales_columnas.append(nombre_total_alti)
        
        todas_las_cols_tmpc = cols_tmpc + ([nombre_total_tmpc] if cols_tmpc else [])
        
        for col_t in todas_las_cols_tmpc:
            if col_t in df_pivot.columns:
                df_pivot[col_t] = df_pivot[col_t].round(0).astype("Int64")
        
        columnas_meses = [c for c in df_pivot.columns if c != 'Etiquetas de fila' and c not in totales_columnas]
        orden_final_columnas = ['Etiquetas de fila'] + totales_columnas + columnas_meses
        
        df_final = df_pivot[orden_final_columnas]
        
        return df_final, "Éxito"
        
    except Exception as e:
        return None, str(e)
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

def obtener_coordenadas(icao_code):
    """
    Retorna las coordenadas geográficas de la estación para el mapa de Streamlit.
    """
    try:
        airports = airportsdata.load('ICAO')
        if icao_code in airports:
            lat = airports[icao_code]['lat']
            lon = airports[icao_code]['lon']
            return pd.DataFrame({'lat': [lat], 'lon': [lon]})
        return None
    except:
        return None

def procesar_meteorologia(station, fecha_inicio, fecha_fin, lista_variables):
    """
    Construye la matriz dinámica mensual base con las columnas mensuales puras,
    permitiendo que la aplicación de Streamlit maneje los totales de forma dinámica.
    """
    try:
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
            
        df = pd.read_csv(io.StringIO("\n".join(datos_limpios)))
        df['valid'] = pd.to_datetime(df['valid'])
        
        columnas_tecnicas = [mapeo_iem[v] for v in lista_variables if v in mapeo_iem]
        for col in columnas_tecnicas:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df['Etiquetas de fila'] = df['valid'].dt.strftime('%I %p')
        df['Mes'] = df['valid'].dt.strftime('%b')
        
        meses_ordenados = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        meses_en_datos = [m for m in meses_ordenados if m in df['Mes'].unique()]
        df['Mes'] = pd.Categorical(df['Mes'], categories=meses_en_datos, ordered=True)
        
        horas_ordenadas = pd.date_range("00:00", "23:00", freq="h").strftime('%I %p').tolist()
        df['Etiquetas de fila'] = pd.Categorical(df['Etiquetas de fila'], categories=horas_ordenadas, ordered=True)

        df_pivot = df.pivot_table(
            values=columnas_tecnicas,
            index='Etiquetas de fila',
            columns='Mes',
            aggfunc='mean',
            observed=False
        ).round(2)
        
        df_pivot.columns = [f"{mes}_{var}" for var, mes in df_pivot.columns]
        df_pivot = df_pivot.reset_index()
        
        # Mantenemos las columnas de temperatura como floats originales para conservar la precisión total
        # al momento de calcular los promedios en app.py
        cols_tmpc = [c for c in df_pivot.columns if '_tmpc' in c]
        for col_t in cols_tmpc:
            df_pivot[col_t] = pd.to_numeric(df_pivot[col_t], errors='coerce')
            
        return df_pivot, "Éxito"
        
    except Exception as e:
        return None, str(e)
