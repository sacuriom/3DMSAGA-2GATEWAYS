from pathlib import Path
import csv,json,math,re,base64,collections,hashlib,shutil,datetime as dt
import numpy as np

HERE=Path(__file__).resolve().parent
if (HERE/'26octRuta2Test.csv').exists() and (HERE/'extraccion_tts').exists():
    O=HERE;R=HERE.parent;source=HERE/'26octRuta2Test.csv'
else:
    R=HERE;O=R/'validacion_ruta2_20261026';source=Path('C:/Users/sacur/AppData/Local/Temp/26octRuta2Test.csv')
O.mkdir(exist_ok=True)
if source.resolve()!=(O/source.name).resolve():shutil.copy2(source,O/source.name)
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def number(x):
    try:return float(x)
    except (ValueError,TypeError):return math.nan
def coord(x):
    if not x or x.strip()=='-':return math.nan
    v=number(re.sub(r'[^0-9.+-]','',x))
    return -abs(v) if any(h in x.upper() for h in ('S','W')) else v
def utc(x):return dt.datetime.fromisoformat(x.replace('Z','+00:00'))
def write(name,rows):
    if not rows:return
    with (O/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
folder=O/'extraccion_tts/20261026T200441Z'
objs=[]
for line in (folder/'respuesta_original.jsonl').read_text(encoding='utf-8').splitlines():
    s=line.strip()
    if s.startswith('data:'):s=s[5:].strip()
    if s.startswith('{'):objs.append(json.loads(s))
raw=read(source)
assert [int(r['Tx Cnt']) for r in raw]==list(range(1,len(raw)+1))
ft=[]
for r in raw:
    local=dt.datetime.strptime(r['Time'],'%Y-%m-%d %H:%M:%S');u=local.replace(tzinfo=dt.timezone(dt.timedelta(hours=-5))).astimezone(dt.timezone.utc)
    ft.append(dict(Tx_Cnt=int(r['Tx Cnt']),Time_FT_original=r['Time'],Time_FT_assuming_UTC_minus5=u.isoformat(),FT_RSSI_dBm=number(r['RSSI (dBm)']),FT_SNR_dB=number(r['SNR (dB)']),Longitude=coord(r['Longitude']),Latitude=coord(r['Latitude']),SF=r['SF'],Power=r['TX Power'],Uplink_counter=int(r['UPlink Packet']),Confirm_counter=int(r['Confirm Packet'])))
test=[];reports=[]
for o in objs:
    r=o['result'];u=r['uplink_message'];payload=base64.b64decode(u['frm_payload']).hex()
    row=dict(server_time=r['received_at'],radio_time=u['settings'].get('time',''),device=r['end_device_ids']['device_id'],dev_addr=r['end_device_ids'].get('dev_addr',''),fcnt=u['f_cnt'],payload_hex=payload,sf=u['settings']['data_rate']['lora']['spreading_factor'],bw=u['settings']['data_rate']['lora']['bandwidth'],cr=u['settings']['data_rate']['lora'].get('coding_rate'),frequency=u['settings']['frequency'],rx=u['rx_metadata'])
    (test if payload=='ff' else reports).append(row)
assert len(set((r['dev_addr'],r['fcnt']) for r in test))==len(test)
assert len(set(r['dev_addr'] for r in test))==1
bycount={r['fcnt']:r for r in test};joined=[];receptions=[];last_confirm=0
for r in ft:
    seq=r['Tx_Cnt'];t=bycount.get(seq+1);ack_increment=r['Confirm_counter']-last_confirm;last_confirm=r['Confirm_counter']
    gw=set(x['gateway_ids']['gateway_id'] for x in t['rx']) if t else set()
    p=dict(**r,Expected_FCnt=seq+1,TTS_received=bool(t),FT_ack_increment=ack_increment,Gateway1_received='gateway1' in gw,Gateway2_received='gateway2' in gw,Distinct_gateways=len(gw),TTS_server_time=t['server_time'] if t else '',TTS_radio_time=t['radio_time'] if t else '',FT_time_minus_TTS_radio_s=(utc(r['Time_FT_assuming_UTC_minus5'])-utc(t['radio_time'])).total_seconds() if t and t['radio_time'] else None)
    for gwname in ('gateway1','gateway2'):
        rx=next((x for x in t['rx'] if x['gateway_ids']['gateway_id']==gwname),None) if t else None
        p[gwname+'_RSSI_dBm']=rx.get('rssi') if rx else None;p[gwname+'_SNR_dB']=rx.get('snr') if rx else None
    joined.append(p)
    if t:
        for x in t['rx']:
            receptions.append(dict(Tx_Cnt=seq,FCnt=t['fcnt'],Dev_Addr=t['dev_addr'],Time_FT_original=r['Time_FT_original'],Time_TTS_radio=t['radio_time'],Time_TTS_server=t['server_time'],Latitude_FT=r['Latitude'],Longitude_FT=r['Longitude'],Gateway_ID=x['gateway_ids']['gateway_id'],RSSI_uplink_dBm=x.get('rssi'),SNR_uplink_dB=x.get('snr'),SF=t['sf'],BW_Hz=t['bw'],Coding_Rate=t['cr'],Frequency_Hz=t['frequency']))
write('cruce_FT_TTS_764.csv',joined);write('recepciones_pruebas_por_gateway.csv',receptions)
write('reportes_no_prueba.csv',[{k:v for k,v in r.items() if k!='rx'} for r in reports])
write('filas_sin_recepcion_TTS.csv',[r for r in joined if not r['TTS_received']])
write('discrepancias_confirmacion.csv',[r for r in joined if bool(r['FT_ack_increment'])!=r['TTS_received']])
times=np.array([utc(r['Time_FT_assuming_UTC_minus5']).timestamp() for r in ft]);diffs=np.diff(times)
deltas=np.array([r['FT_time_minus_TTS_radio_s'] for r in joined if r['TTS_received']]);validgps=[r for r in joined if math.isfinite(r['Latitude']) and math.isfinite(r['Longitude'])]
g1=sum(r['Gateway1_received'] for r in joined);g2=sum(r['Gateway2_received'] for r in joined);both=sum(r['Distinct_gateways']==2 for r in joined)
summary=dict(ft_rows=len(raw),ft_first=raw[0]['Time'],ft_last=raw[-1]['Time'],ft_span_minutes=(times[-1]-times[0])/60,ft_rssi_finite=sum(math.isfinite(r['FT_RSSI_dBm']) for r in ft),ft_confirm_final=ft[-1]['Confirm_counter'],ft_ack_counter_increments=dict(collections.Counter(r['FT_ack_increment'] for r in joined)),sf_counts=dict(collections.Counter(r['SF'] for r in ft)),power_counts=dict(collections.Counter(r['Power'] for r in ft)),gps_valid_rows=len(validgps),gps_missing_rows=len(ft)-len(validgps),gps_first=validgps[0]['Time_FT_original'] if validgps else None,gps_unique_positions=len(set((r['Latitude'],r['Longitude']) for r in validgps)),interval_s=dict(median=float(np.median(diffs)),min=float(diffs.min()),max=float(diffs.max()),gt_20s=int((diffs>20).sum())),tts_all_records=len(objs),tts_test_records=len(test),tts_non_test_reports=len(reports),tts_test_fcnt_min=min(bycount),tts_test_fcnt_max=max(bycount),tts_test_device=sorted(set(r['device'] for r in test)),tts_test_dev_addr=sorted(set(r['dev_addr'] for r in test)),tts_test_reception_entries=len(receptions),received_test_count=sum(r['TTS_received'] for r in joined),missing_test_count=sum(not r['TTS_received'] for r in joined),unmapped_test_fcnt=sorted(set(bycount)-set(r['Tx_Cnt']+1 for r in ft)),gateway1_count=g1,gateway2_count=g2,both_count=both,only_gateway1=g1-both,only_gateway2=g2-both,observed_test_reception_pct=100*len(test)/len(ft),ft_confirmation_pct=100*ft[-1]['Confirm_counter']/len(ft),double_reception_pct_received=100*both/len(test),double_reception_pct_test_rows=100*both/len(ft),timing_delta_s=dict(median=float(np.median(deltas)),min=float(deltas.min()),max=float(deltas.max()),p05=float(np.percentile(deltas,5)),p95=float(np.percentile(deltas,95))),ack_tts_disagreements=[r['Tx_Cnt'] for r in joined if bool(r['FT_ack_increment'])!=r['TTS_received']],input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),tts_raw_sha256=hashlib.sha256((folder/'respuesta_original.jsonl').read_bytes()).hexdigest(),association_rule='FCnt = Tx_Cnt + 1, within single observed DevAddr, test payload ff. Chronology and end report delimit session; local timezone UTC-5 is an interpretation supported by alignment.',gps_bounds=dict(lat_min=min(r['Latitude'] for r in validgps),lat_max=max(r['Latitude'] for r in validgps),lon_min=min(r['Longitude'] for r in validgps),lon_max=max(r['Longitude'] for r in validgps)))
pergw=[]
for gw in ('gateway1','gateway2'):
    subset=[r for r in receptions if r['Gateway_ID']==gw];rr=np.array([number(r['RSSI_uplink_dBm']) for r in subset]);ss=np.array([number(r['SNR_uplink_dB']) for r in subset])
    pergw.append(dict(gateway=gw,receptions=len(subset),rssi_min=float(np.nanmin(rr)),rssi_median=float(np.nanmedian(rr)),rssi_max=float(np.nanmax(rr)),snr_present=int(np.isfinite(ss).sum()),snr_min=float(np.nanmin(ss)),snr_median=float(np.nanmedian(ss)),snr_max=float(np.nanmax(ss))))
summary['per_gateway']=pergw;summary['matched_receipts_with_gps']=sum(r['TTS_received'] for r in validgps)
summary['ft_rssi_minus_strongest_uplink_median_dB']=float(np.median([r['FT_RSSI_dBm']-max(r['gateway1_RSSI_dBm'] if r['gateway1_RSSI_dBm'] is not None else -math.inf,r['gateway2_RSSI_dBm'] if r['gateway2_RSSI_dBm'] is not None else -math.inf) for r in joined if r['TTS_received'] and math.isfinite(r['FT_RSSI_dBm'])]))
def distance(lat1,lon1,lat2,lon2):
    a,b,c,d=map(math.radians,[lat1,lon1,lat2,lon2]);return 6371000*2*math.asin(min(1,math.sqrt(math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2)))
for r in joined:
    r['Distance_Paltas_m']=distance(r['Latitude'],r['Longitude'],-1.25160,-78.62772) if math.isfinite(r['Latitude']) else math.nan
    r['Distance_PUCESA_m']=distance(r['Latitude'],r['Longitude'],-1.27458,-78.63920) if math.isfinite(r['Latitude']) else math.nan
    r['Grid100m_ID']=f"{math.floor((r['Longitude']+78.63)*111320*math.cos(math.radians(-1.26))/100)}:{math.floor((r['Latitude']+1.26)*111320/100)}" if math.isfinite(r['Latitude']) else ''
validgps=[r for r in joined if math.isfinite(r['Latitude']) and math.isfinite(r['Longitude'])]
geosegments=[]
for label,predicate in [('GPS valido',lambda r:True),('Dentro 100 m Paltas',lambda r:r['Distance_Paltas_m']<=100),('Dentro 100 m PUCESA',lambda r:r['Distance_PUCESA_m']<=100),('Fuera de 100 m de ambos',lambda r:r['Distance_Paltas_m']>100 and r['Distance_PUCESA_m']>100)]:
    s=[r for r in validgps if predicate(r)];n=len(s)
    geosegments.append(dict(subset=label,rows=n,received=sum(r['TTS_received'] for r in s),both=sum(r['Distinct_gateways']==2 for r in s),received_pct=100*sum(r['TTS_received'] for r in s)/n if n else None))
write('resumen_por_entorno.csv',geosegments)
cells=[]
for cell in sorted(set(r['Grid100m_ID'] for r in validgps)):
    s=[r for r in validgps if r['Grid100m_ID']==cell];cells.append(dict(cell=cell,n=len(s),received=sum(r['TTS_received'] for r in s),gateway1=sum(r['Gateway1_received'] for r in s),gateway2=sum(r['Gateway2_received'] for r in s),both=sum(r['Distinct_gateways']==2 for r in s),lat_mean=float(np.mean([r['Latitude'] for r in s])),lon_mean=float(np.mean([r['Longitude'] for r in s]))))
write('resumen_celdas100m.csv',cells)
legs=[distance(a['Latitude'],a['Longitude'],b['Latitude'],b['Longitude']) for a,b in zip(validgps[:-1],validgps[1:])]
gps_checks=[];flagged=set()
for a,b,dist in zip(validgps[:-1],validgps[1:],legs):
    gap=(utc(b['Time_FT_assuming_UTC_minus5'])-utc(a['Time_FT_assuming_UTC_minus5'])).total_seconds();speed=3.6*dist/gap
    if speed>120:
        flagged.update((a['Tx_Cnt'],b['Tx_Cnt']))
        gps_checks.append(dict(From_Tx_Cnt=a['Tx_Cnt'],To_Tx_Cnt=b['Tx_Cnt'],Time_from=a['Time_FT_original'],Time_to=b['Time_FT_original'],step_m=dist,gap_s=gap,implied_speed_kmh=speed,flag='Plausibility warning >120 km/h; not an automatic data exclusion'))
write('alertas_GPS.csv',gps_checks)
for r in joined:r['GPS_jump_warning']=r['Tx_Cnt'] in flagged
cutoff=dt.datetime(2026,10,26,14,0,0)
for r in joined:r['Phase_approx14']=('Preparation_stationary' if dt.datetime.fromisoformat(r['Time_FT_original'])<cutoff else 'Vehicle_test_window')
phase_summaries=[]
for label in ('Preparation_stationary','Vehicle_test_window'):
    s=[r for r in joined if r['Phase_approx14']==label];gps=[r for r in s if math.isfinite(r['Latitude'])];n=len(s)
    speeds=[];ds=[]
    for a,b in zip(gps[:-1],gps[1:]):
        dd=distance(a['Latitude'],a['Longitude'],b['Latitude'],b['Longitude']);gg=(utc(b['Time_FT_assuming_UTC_minus5'])-utc(a['Time_FT_assuming_UTC_minus5'])).total_seconds();ds.append(dd);speeds.append(3.6*dd/gg)
    phase_summaries.append(dict(phase=label,first=s[0]['Time_FT_original'],last=s[-1]['Time_FT_original'],ft_rows=n,received=sum(r['TTS_received'] for r in s),not_found=sum(not r['TTS_received'] for r in s),gateway1=sum(r['Gateway1_received'] for r in s),gateway2=sum(r['Gateway2_received'] for r in s),both=sum(r['Distinct_gateways']==2 for r in s),only_gateway1=sum(r['Gateway1_received'] and not r['Gateway2_received'] for r in s),only_gateway2=sum(r['Gateway2_received'] and not r['Gateway1_received'] for r in s),reception_pct=100*sum(r['TTS_received'] for r in s)/n,gps_rows=len(gps),gps_cells100m=len(set(r['Grid100m_ID'] for r in gps)),gps_polyline_sum_km=sum(ds)/1000,gps_max_step_m=max(ds),gps_steps_over120kmh=sum(v>120 for v in speeds)))
write('resumen_fases.csv',phase_summaries);summary['phases_approx14']=phase_summaries
write('cruce_recorrido_desde14.csv',[r for r in joined if r['Phase_approx14']=='Vehicle_test_window'])
sens=[]
for boundary in ('13:55:00','14:00:00','14:05:00'):
    s=[r for r in joined if r['Time_FT_original']>='2026-10-26 '+boundary];n=len(s)
    sens.append(dict(start_approx=boundary,rows=n,received=sum(r['TTS_received'] for r in s),both=sum(r['Distinct_gateways']==2 for r in s),reception_pct=100*sum(r['TTS_received'] for r in s)/n))
summary['start_time_sensitivity']=sens;write('sensibilidad_hora_inicio.csv',sens)
summary['geographic_subsets']=geosegments;summary['grid100m_cells_visited']=len(cells)
summary['gps_polyline_sum_km']=sum(legs)/1000;summary['gps_max_consecutive_step_m']=max(legs)
summary['gps_steps_over_120kmh']=len(gps_checks);summary['gps_rows_adjacent_to_flagged_steps']=len(flagged)
summary['ft_counter_steps_greater_than_one']=sum(r['FT_ack_increment']>1 for r in joined)
summary['scope']='Stored reception of this session, with sequence association rule; not city area coverage, not independent model RF validation.'
write('cruce_FT_TTS_764.csv',joined)
(O/'resumen_validacion.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
write('resumen_por_gateway.csv',pergw)
print(json.dumps(summary,ensure_ascii=False,indent=2))
