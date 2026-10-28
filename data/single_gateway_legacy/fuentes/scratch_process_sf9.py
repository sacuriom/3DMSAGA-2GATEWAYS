"""
Script de Procesamiento Estadístico Riguroso 3D-M-SAGA vs Field Tester SF9 (Optimizado con NumPy)
"""
import os, glob, re, math, json, time
import numpy as np
import pandas as pd

t0 = time.time()

GW_LAT = -1.25164
GW_LON = -78.62765
GW_ALT = 2707.0  # msnm
FREQ_MHZ = 915.0
PTX_DBM = 20.0   # Potencia estándar homologada Ecuador (US915/AU915)
GAIN_DBI = 2.15  # Ganancia antena Gateway UG67
EIRP = PTX_DBM + GAIN_DBI
SENS_SF9 = -130.0 # Sensibilidad SX1302/SX1262 a 125 kHz BW en SF9

def haversine_np(lat1, lon1, lat2_arr, lon2_arr):
    # lat1, lon1: floats en grados
    # lat2_arr, lon2_arr: numpy arrays en grados
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2_arr)
    dphi = phi2 - phi1
    dlam = np.radians(lon2_arr) - np.radians(lon1)
    a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2.0)**2
    return 2.0 * 6371000.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))

def parse_coord(val):
    if pd.isna(val) or not str(val).strip(): return None
    s = str(val).strip().upper()
    is_s = 'S' in s; is_w = 'W' in s
    s_clean = re.sub(r'[^\d.-]', '', s)
    try:
        f = float(s_clean)
        if is_s and f > 0: f = -f
        if is_w and f > 0: f = -f
        if abs(f) > 180 or abs(f) < 0.001: return None
        return round(f, 6)
    except: return None

# 1. Cargar Gemelo Digital
dt_path = r"D:\DOCTORADOUPS\TESIS\OCTUBRE\Master_Validation_US915_SF9_20dBm_20261011_002521\DigitalTwin_Base_Model.csv"
if not os.path.exists(dt_path):
    candidates = glob.glob(r"D:\DOCTORADOUPS\TESIS\OCTUBRE\**\DigitalTwin_Base_Model.csv", recursive=True)
    dt_path = candidates[0]

df_dt = pd.read_csv(dt_path)
print(f"[1] Gemelo Digital cargado: {len(df_dt)} intersecciones desde {os.path.basename(dt_path)}")

# 2. Computar Modelo 3D-M-SAGA
L0 = 20.0 * math.log10(FREQ_MHZ) - 27.55
d_horiz_arr = haversine_np(GW_LAT, GW_LON, df_dt['Lat'].values, df_dt['Lon'].values)
d_vert_arr = df_dt['Altitude_m'].values - GW_ALT
d_3d_arr = np.sqrt(d_horiz_arr**2 + d_vert_arr**2)
d_3d_arr[d_3d_arr < 1.0] = 1.0

# Asignar exponentes morfológicos
n_p_arr = np.full(len(df_dt), 2.65) # Residential por defecto
L_c_arr = np.full(len(df_dt), 2.5)

clutter_str = df_dt['Clutter'].astype(str)
idx_dense = clutter_str.str.contains('Dense', case=False)
idx_park = clutter_str.str.contains('Park|Periphery', case=False)

n_p_arr[idx_dense] = 2.85
L_c_arr[idx_dense] = 5.0

n_p_arr[idx_park] = 2.35
L_c_arr[idx_park] = 0.0

# Atenuación topográfica
diff_alt = GW_ALT - df_dt['Altitude_m'].values
L_topo_arr = np.zeros(len(df_dt))
c_idx = (diff_alt < -10.0)
L_topo_arr[c_idx] = np.minimum(8.0 * np.log10(np.abs(diff_alt[c_idx])), 20.0)

rssi_th_arr = EIRP - L0 - (10.0 * n_p_arr * np.log10(d_3d_arr)) - L_c_arr - L_topo_arr
is_covered_arr = (rssi_th_arr >= SENS_SF9).astype(int)

df_dt['Dist_3D_m'] = np.round(d_3d_arr, 1)
df_dt['Dist_2D_m'] = np.round(d_horiz_arr, 1)
df_dt['RSSI_3DMSAGA_SF9'] = np.round(rssi_th_arr, 2)
df_dt['Covered_3DMSAGA_SF9'] = is_covered_arr

print(f"[2] Modelo 3D-M-SAGA SF9 computado:")
print(f"    Rango RSSI teórico: {df_dt['RSSI_3DMSAGA_SF9'].min()} dBm a {df_dt['RSSI_3DMSAGA_SF9'].max()} dBm")
print(f"    Nodos con cobertura modelada: {is_covered_arr.sum()} / {len(df_dt)} ({is_covered_arr.sum()/len(df_dt)*100:.1f}%)")

# 3. Cargar las 4 Rutas Planificadas de rutas_fieldtester.js
planned_routes_pts = {}
try:
    with open(r"D:\DOCTORADOUPS\TESIS\OCTUBRE\rutas_fieldtester.js", "r", encoding="utf-8") as f:
        rjs = f.read()
    match = re.search(r"window\.RUTAS_FIELDTESTER\s*=\s*(\{.*\});?", rjs, re.DOTALL)
    if match:
        rutas_data = json.loads(match.group(1))
        for c_idx, circ in enumerate(rutas_data.get('circuits', [])):
            r_name = f"Ruta {c_idx+1}"
            for p in circ.get('points', []):
                planned_routes_pts[(round(p['Lat'], 5), round(p['Lon'], 5))] = r_name
        print(f"[3] Rutas planificadas cargadas: {len(planned_routes_pts)} waypoints.")
except Exception as e:
    print(f"[3] Advertencia al cargar rutas planificadas: {e}")

# 4. Ingesta de Datos Empíricos del Field Tester con SF9
print("[4] Ingestando datos de telemetría de campo...")

all_csvs = sorted(glob.glob(r"D:\DOCTORADOUPS\TESIS\OCTUBRE\FieldTester\**\*.csv", recursive=True))
empirical_pings = []

for f in all_csvs:
    fname = os.path.basename(f)
    parent = os.path.basename(os.path.dirname(f))
    if 'noise' in fname.lower(): continue
    
    try:
        df = pd.read_csv(f)
        cols = {c.strip().lower(): c for c in df.columns}
        lat_c = next((cols[k] for k in cols if 'lat' in k), None)
        lon_c = next((cols[k] for k in cols if 'lon' in k or 'lng' in k), None)
        rssi_c = next((cols[k] for k in cols if 'rssi' in k and 'rssis' not in k), None)
        snr_c = next((cols[k] for k in cols if 'snr' in k), None)
        sf_c = next((cols[k] for k in cols if 'sf' in k), None)
        sig_c = next((cols[k] for k in cols if 'signal' in k or 'status' in k), None)
        time_c = next((cols[k] for k in cols if 'time' in k or 'date' in k), None)
        loss_c = next((cols[k] for k in cols if 'loss' in k), None)
        
        if not lat_c or not lon_c: continue
        
        for idx, r in df.iterrows():
            la = parse_coord(r[lat_c])
            lo = parse_coord(r[lon_c])
            if la is None or lo is None: continue
            if not (-1.35 <= la <= -1.15 and -78.75 <= lo <= -78.50): continue
            
            # Detect SF
            sf_val = 'SF9'
            if sf_c and pd.notna(r[sf_c]):
                sfs = str(r[sf_c]).upper()
                if 'SF9' in sfs: sf_val = 'SF9'
                elif 'SF7' in sfs: sf_val = 'SF7'
                elif 'SF8' in sfs: sf_val = 'SF8'
                elif 'SF10' in sfs: sf_val = 'SF10'
                else: sf_val = sfs
            else:
                m = re.search(r'SF(\d+)', fname, re.I)
                if m: sf_val = 'SF' + m.group(1)
                elif 'jona' in fname.lower() or 'au915' in parent.lower(): sf_val = 'SF9'
                
            if sf_val != 'SF9':
                continue
                
            rs_val = None
            if rssi_c and pd.notna(r[rssi_c]):
                try:
                    v = float(str(r[rssi_c]).strip())
                    if -140.0 <= v <= 0.0: rs_val = v
                except: pass
                
            snr_val = None
            if snr_c and pd.notna(r[snr_c]):
                try: snr_val = float(str(r[snr_c]).strip())
                except: pass
                
            sig_val = str(r[sig_c]).strip() if sig_c and pd.notna(r[sig_c]) else ''
            time_val = str(r[time_c]).strip() if time_c and pd.notna(r[time_c]) else ''
            
            loss_val = None
            if loss_c and pd.notna(r[loss_c]):
                try: loss_val = float(str(r[loss_c]).replace('%','').strip())
                except: pass
            has_ack = (rs_val is not None)
                
            campaign = '11-Octubre' if '11oct' in parent.lower() or '11oct' in fname.lower() else (
                       '10-Octubre' if '10oct' in parent.lower() or '10oct' in fname.lower() else 'AU915-Historico')
            
            file_route = 'Desconocida'
            fn_low = fname.lower()
            if 'ruta1' in fn_low: file_route = 'Ruta 1'
            elif 'ruta2' in fn_low: file_route = 'Ruta 2'
            elif 'ruta3' in fn_low: file_route = 'Ruta 3'
            elif 'ruta4' in fn_low: file_route = 'Ruta 4'
            
            empirical_pings.append({
                'Campaign': campaign,
                'File': fname,
                'File_Route': file_route,
                'Lat': la,
                'Lon': lo,
                'RSSI': rs_val,
                'SNR': snr_val,
                'Signal': sig_val,
                'Packet_Loss': loss_val,
                'Time': time_val,
                'Has_ACK': has_ack
            })
    except Exception as e:
        pass

df_emp = pd.DataFrame(empirical_pings)
print(f"    Total pings SF9 georreferenciados: {len(df_emp)}")
print(f"    Pings con ACK exitoso: {df_emp['Has_ACK'].sum()}")
print(f"    Pings con pérdida/punto ciego (Sin ACK): {(~df_emp['Has_ACK']).sum()}")

# 5. Algoritmo Z-Snapping Vectorizado Ultra-Rápido con NumPy
print("[5] Ejecutando Z-Snapping ultra-rápido hacia los 2,154 nodos urbanos...")
TOLERANCE_RADIUS_M = 50.0

emp_lats = df_emp['Lat'].values
emp_lons = df_emp['Lon'].values
emp_has_ack = df_emp['Has_ACK'].values
emp_rssi = df_emp['RSSI'].values
emp_snr = df_emp['SNR'].values
emp_camps = df_emp['Campaign'].values
emp_froutes = df_emp['File_Route'].values

nodes_matched_list = []

for n_idx, nrow in df_dt.iterrows():
    n_lat = nrow['Lat']
    n_lon = nrow['Lon']
    
    # Distancias vectorizadas en metros
    dists = haversine_np(n_lat, n_lon, emp_lats, emp_lons)
    matched_indices = np.where(dists <= TOLERANCE_RADIUS_M)[0]
    
    # Identificar ruta planificada
    assigned_route = "Fuera_de_Rutas"
    for (plat, plon), rname in planned_routes_pts.items():
        if math.hypot(n_lat - plat, n_lon - plon) < 0.0006: # ~60m
            assigned_route = rname
            break
            
    if len(matched_indices) == 0:
        nodes_matched_list.append({
            'Node_ID': n_idx + 1,
            'Calle_1': nrow['Street_1'],
            'Calle_2': nrow['Street_2'],
            'Lat': n_lat,
            'Lon': n_lon,
            'Altitud_m': nrow['Altitude_m'],
            'Clutter': nrow['Clutter'],
            'Dist_GW_m': nrow['Dist_2D_m'],
            'Ruta': assigned_route,
            'RSSI_Teorico_dBm': nrow['RSSI_3DMSAGA_SF9'],
            'Cobertura_Modelada': nrow['Covered_3DMSAGA_SF9'],
            'Visitado_Empirico': False,
            'Total_Pings_Empiricos': 0,
            'ACKs_Exitosos': 0,
            'Fallos_Timeout': 0,
            'RSSI_Empirico_dBm': np.nan,
            'SNR_Empirico_dB': np.nan,
            'Estado_Empirico': 'No_Visitado',
            'Punto_Ciego_Empirico': False,
            'Campañas_Detectadas': '',
            'Error_Residual_dB': np.nan,
            'Dentro_Margen_6dB': np.nan,
            'Dentro_Margen_10dB': np.nan,
            'Clasificacion_Cobertura': 'No_Evaluado_In_Situ'
        })
    else:
        m_has_ack = emp_has_ack[matched_indices]
        m_rssi = emp_rssi[matched_indices]
        m_snr = emp_snr[matched_indices]
        m_camps = emp_camps[matched_indices]
        m_froutes = emp_froutes[matched_indices]
        
        total_pings = len(matched_indices)
        num_acks = int(np.sum(m_has_ack))
        num_fails = total_pings - num_acks
        camps_str = ",".join(np.unique(m_camps))
        
        if assigned_route == "Fuera_de_Rutas":
            valid_r = [fr for fr in m_froutes if fr != 'Desconocida']
            if valid_r:
                assigned_route = pd.Series(valid_r).mode()[0]
                
        if num_acks > 0:
            ack_mask = (m_has_ack == True)
            ack_rssis = m_rssi[ack_mask]
            ack_snrs = m_snr[ack_mask]
            
            best_idx = np.nanargmax(ack_rssis)
            best_rssi = float(ack_rssis[best_idx])
            best_snr = float(ack_snrs[best_idx]) if pd.notna(ack_snrs[best_idx]) else np.nan
            
            estado_emp = 'Cubierto_Con_Enlace'
            punto_ciego = False
            err = round(best_rssi - nrow['RSSI_3DMSAGA_SF9'], 2)
            d6 = 1 if abs(err) <= 6.0 else 0
            d10 = 1 if abs(err) <= 10.0 else 0
            
            cov_theo = nrow['Covered_3DMSAGA_SF9'] == 1
            cov_real = best_rssi >= SENS_SF9
            if cov_theo and cov_real: clasif = 'True_Positive (Ambos Cubierto)'
            elif not cov_theo and not cov_real: clasif = 'True_Negative (Ambos Sin Cobertura)'
            elif cov_theo and not cov_real: clasif = 'False_Positive (Modelo predice pero canal real falla)'
            else: clasif = 'False_Negative (Canal enlaza pero modelo preveía límite)'
        else:
            best_rssi = np.nan
            best_snr = np.nan
            estado_emp = 'Punto_Ciego_Sin_ACK'
            punto_ciego = True
            err = np.nan
            d6 = np.nan
            d10 = np.nan
            clasif = 'Punto_Ciego_Confirmado (Packet Loss 100%)'
            
        nodes_matched_list.append({
            'Node_ID': n_idx + 1,
            'Calle_1': nrow['Street_1'],
            'Calle_2': nrow['Street_2'],
            'Lat': n_lat,
            'Lon': n_lon,
            'Altitud_m': nrow['Altitude_m'],
            'Clutter': nrow['Clutter'],
            'Dist_GW_m': nrow['Dist_2D_m'],
            'Ruta': assigned_route,
            'RSSI_Teorico_dBm': nrow['RSSI_3DMSAGA_SF9'],
            'Cobertura_Modelada': nrow['Covered_3DMSAGA_SF9'],
            'Visitado_Empirico': True,
            'Total_Pings_Empiricos': total_pings,
            'ACKs_Exitosos': num_acks,
            'Fallos_Timeout': num_fails,
            'RSSI_Empirico_dBm': best_rssi,
            'SNR_Empirico_dB': best_snr,
            'Estado_Empirico': estado_emp,
            'Punto_Ciego_Empirico': punto_ciego,
            'Campañas_Detectadas': camps_str,
            'Error_Residual_dB': err,
            'Dentro_Margen_6dB': d6,
            'Dentro_Margen_10dB': d10,
            'Clasificacion_Cobertura': clasif
        })

df_master = pd.DataFrame(nodes_matched_list)
df_vis = df_master[df_master['Visitado_Empirico'] == True]
df_ack = df_master[df_master['Estado_Empirico'] == 'Cubierto_Con_Enlace']
df_blind = df_master[df_master['Estado_Empirico'] == 'Punto_Ciego_Sin_ACK']

# 6. Métricas Estadísticas
errors = df_ack['Error_Residual_dB'].dropna().values
rmse = np.sqrt(np.mean(errors**2))
mae = np.mean(np.abs(errors))
bias = np.mean(errors)
std_err = np.std(errors)
sim_6db = (np.sum(np.abs(errors) <= 6.0) / len(errors)) * 100.0
sim_10db = (np.sum(np.abs(errors) <= 10.0) / len(errors)) * 100.0

theo_vals = df_ack['RSSI_Teorico_dBm'].values
emp_vals = df_ack['RSSI_Empirico_dBm'].values
corr_r = np.corrcoef(theo_vals, emp_vals)[0, 1]
r2 = corr_r**2

print("\n" + "="*75)
print("   ESTADÍSTICAS COMPARATIVAS RIGUROSAS: 3D-M-SAGA vs FIELD TESTER (SF9)")
print("="*75)
print(f"  • Total Nodos del Gemelo Digital:        {len(df_master)}")
print(f"  • Total Nodos Evaluados Empíricamente:   {len(df_vis)}")
print(f"  • Nodos con Enlace Exitoso (ACK):        {len(df_ack)} ({len(df_ack)/len(df_vis)*100:.1f}%)")
print(f"  • Nodos en Puntos Ciegos (Pérdida 100%): {len(df_blind)} ({len(df_blind)/len(df_vis)*100:.1f}%)")
print(f"  • Error Cuadrático Medio (RMSE):         {rmse:.2f} dB")
print(f"  • Error Absoluto Medio (MAE):            {mae:.2f} dB")
print(f"  • Sesgo Medio (Bias = Emp - Theo):       {bias:+.2f} dB")
print(f"  • Desviación Estándar (sigma):           {std_err:.2f} dB")
print(f"  • Similitud RF bajo UIT-R P.1411 (±6dB): {sim_6db:.1f}%")
print(f"  • Similitud RF extendida (±10dB):        {sim_10db:.1f}%")
print(f"  • Coeficiente de Correlación Pearson (r):{corr_r:.3f}")
print(f"  • Coeficiente de Determinación (R²):     {r2:.3f}")
print(f"  • Rango Máximo Empírico Alcanzado (SF9): {df_ack['Dist_GW_m'].max():.1f} m")
print(f"  • Rango Máximo Teórico del Modelo:       {df_master[df_master['Cobertura_Modelada']==1]['Dist_GW_m'].max():.1f} m")
print("="*75)

# Estadísticas por Ruta
print("\nDesglose de las 4 Rutas de Cobertura:")
rutas_stats = []
for r_name in ['Ruta 1', 'Ruta 2', 'Ruta 3', 'Ruta 4']:
    sub_r = df_master[df_master['Ruta'] == r_name]
    sub_vis = sub_r[sub_r['Visitado_Empirico'] == True]
    sub_ack = sub_r[sub_r['Estado_Empirico'] == 'Cubierto_Con_Enlace']
    sub_blind = sub_r[sub_r['Estado_Empirico'] == 'Punto_Ciego_Sin_ACK']
    err_r = sub_ack['Error_Residual_dB'].dropna().values
    rmse_r = np.sqrt(np.mean(err_r**2)) if len(err_r) > 0 else np.nan
    mae_r = np.mean(np.abs(err_r)) if len(err_r) > 0 else np.nan
    s6_r = (np.sum(np.abs(err_r) <= 6.0) / len(err_r) * 100.0) if len(err_r) > 0 else np.nan
    max_d_r = sub_ack['Dist_GW_m'].max() if len(sub_ack) > 0 else 0
    tasa_cov = (len(sub_ack)/len(sub_vis)*100.0) if len(sub_vis) > 0 else 0.0
    
    rutas_stats.append({
        'Ruta': r_name,
        'Nodos_Totales_Ruta': len(sub_r),
        'Nodos_Evaluados': len(sub_vis),
        'Nodos_Con_Enlace': len(sub_ack),
        'Puntos_Ciegos': len(sub_blind),
        'Tasa_Cobertura_Real_pct': round(tasa_cov, 1),
        'RMSE_dB': round(rmse_r, 2) if not np.isnan(rmse_r) else None,
        'MAE_dB': round(mae_r, 2) if not np.isnan(mae_r) else None,
        'Similitud_6dB_pct': round(s6_r, 1) if not np.isnan(s6_r) else None,
        'Rango_Max_m': round(max_d_r, 1)
    })
    print(f"  {r_name}: Nodos Planificados={len(sub_r)}, Evaluados={len(sub_vis)}, Enlace ACK={len(sub_ack)}, Puntos Ciegos={len(sub_blind)}, Cobertura Real={tasa_cov:.1f}%, Rango Max={max_d_r:.0f}m, RMSE={rmse_r:.2f}dB, Similitud ±6dB={s6_r:.1f}%")

# 7. Exportar CSVs
out_csv_all = r"D:\DOCTORADOUPS\TESIS\OCTUBRE\Comparativa_3DMSAGA_vs_FieldTester_SF9_Consolidado.csv"
df_master.to_csv(out_csv_all, index=False, encoding='utf-8-sig')
print(f"\n✓ Archivo maestro exportado: {out_csv_all} ({len(df_master)} registros)")

out_csv_eval = r"D:\DOCTORADOUPS\TESIS\OCTUBRE\Puntos_Evaluados_3DMSAGA_vs_FieldTester_SF9.csv"
df_vis.to_csv(out_csv_eval, index=False, encoding='utf-8-sig')
print(f"✓ Archivo de puntos evaluados exportado: {out_csv_eval} ({len(df_vis)} registros)")

out_csv_blind = r"D:\DOCTORADOUPS\TESIS\OCTUBRE\Puntos_Ciegos_Identificados_SF9.csv"
df_blind.to_csv(out_csv_blind, index=False, encoding='utf-8-sig')
print(f"✓ Archivo de puntos ciegos exportado: {out_csv_blind} ({len(df_blind)} registros)")

summary_dict = {
    'generated_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
    'elapsed_seconds': round(time.time() - t0, 2),
    'sf': 'SF9',
    'sensibilidad_dbm': SENS_SF9,
    'ptx_dbm': PTX_DBM,
    'total_nodos_modelo': len(df_master),
    'nodos_evaluados_campo': len(df_vis),
    'nodos_con_enlace_ack': len(df_ack),
    'nodos_puntos_ciegos': len(df_blind),
    'tasa_cobertura_real_pct': round((len(df_ack)/len(df_vis))*100.0, 1),
    'rmse_db': round(rmse, 2),
    'mae_db': round(mae, 2),
    'bias_db': round(bias, 2),
    'std_err_db': round(std_err, 2),
    'similitud_6db_pct': round(sim_6db, 1),
    'similitud_10db_pct': round(sim_10db, 1),
    'pearson_r': round(corr_r, 3),
    'r2': round(r2, 3),
    'max_dist_m': round(df_ack['Dist_GW_m'].max(), 1),
    'rutas_stats': rutas_stats
}

with open(r"D:\DOCTORADOUPS\TESIS\OCTUBRE\resumen_comparativo_sf9.json", "w", encoding="utf-8") as f:
    json.dump(summary_dict, f, indent=2, ensure_ascii=False)
print("✓ Resumen estadístico JSON guardado con éxito.")
print(f"✓ Cómputo completado en {time.time() - t0:.2f} segundos.")
