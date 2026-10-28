"""Auditoria reproducible de la repeticion de Ruta 4, sin ajustar predicciones."""
from pathlib import Path
import csv,json,hashlib,math,re,base64,statistics,collections,datetime as dt,argparse
import numpy as np
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--campaign-root',type=Path,default=ROOT/'validacion_ruta4_20261027')
parser.add_argument('--frozen-dataset',type=Path,default=ROOT/'publicacion_github_2026-10-27/3DMSAGA-2GATEWAYS/src/matlab/datos/nodos_referencia.csv')
parser.add_argument('--prior-network',type=Path,default=ROOT/'publicacion_github_2026-10-27/3DMSAGA-2GATEWAYS/data/field_model_comparison/red_mejor_enlace_intersecciones_sin_anclas.csv')
parser.add_argument('--output',type=Path)
args=parser.parse_args();BASE=args.campaign_root;OUT=args.output or BASE/'resultados';OUT.mkdir(parents=True,exist_ok=True);FROZEN=args.frozen_dataset
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
    if not rows:return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def num(x):
    try:return float(x)
    except (ValueError,TypeError):return math.nan
def geo(s):
    m=re.fullmatch(r'\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*([NSEW])?\s*',s or '')
    return (-abs(float(m[1])) if m[2] in ('S','W') else float(m[1])) if m else math.nan
def metrics(pred,obs):
    x=np.asarray(pred,float);y=np.asarray(obs,float);e=y-x
    if not len(e):return {'n':0}
    return dict(n=len(e),RMSE_dB=float(np.sqrt(np.mean(e**2))),MAE_dB=float(np.mean(abs(e))),Bias_obs_minus_pred_dB=float(e.mean()),P90_abs_dB=float(np.percentile(abs(e),90)),Within6_pct=float(np.mean(abs(e)<=6)*100),Within10_pct=float(np.mean(abs(e)<=10)*100))
def hav(a,b):
    if not all(math.isfinite(x) for x in (*a,*b)):return math.nan
    la,lo,lb,lob=map(math.radians,(*a,*b));h=math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin((lob-lo)/2)**2
    return 6371000*2*math.asin(min(1,math.sqrt(h)))

snap=sorted((BASE/'extraccion_tts').glob('*/respuesta_original.jsonl'))[-1];manifest=json.loads((snap.parent/'manifest.json').read_text())
assert manifest['http_status']==200 and manifest['parse_errors']==0 and not manifest['limit_reached']
events={};non_test=[];all_events=[];zone=dt.timezone(dt.timedelta(hours=-5))
for line_number,line in enumerate(snap.read_text(encoding='utf-8-sig').splitlines(),1):
    if not line.strip():continue
    d=json.loads(line.removeprefix('data:'))['result'];u=d['uplink_message'];ids=d['end_device_ids'];assert ids['device_id']=='fieldtester'
    t=dt.datetime.fromisoformat(u['settings'].get('time',d['received_at']).replace('Z','+00:00')).astimezone(zone).replace(tzinfo=None)
    item=dict(FCnt=int(u['f_cnt']),Time=t,Raw=u,Device=ids,SourceLine=line_number,Payload=base64.b64decode(u.get('frm_payload','')).hex())
    all_events.append(item)
    if item['Payload']!='ff':non_test.append(dict(FCnt=item['FCnt'],Time_radio_local=str(t),Payload_hex=item['Payload'],SourceLine=line_number));continue
    key=(ids.get('dev_addr'),u.get('session_key_id'),int(u['f_cnt']));assert key not in events,'Identidad de trama repetida'
    events[key]=item
assert len({(k[0],k[1]) for k in events})==1,'Revisar sesion antes de unir contadores'
by_counter={x['FCnt']:x for x in events.values()}

# Offset identificado por maxima concordancia temporal global; no se ajusta RSSI.
audited=[];offset_evidence=[];file_stats=[]
for file in sorted((BASE/'fuentes').glob('*.csv')):
    raw=read(file);votes=collections.Counter()
    for r in raw:
        time=dt.datetime.fromisoformat(r['Time'])
        closest=min(events.values(),key=lambda e:abs((time-e['Time']).total_seconds()-9.3))
        delta=(time-closest['Time']).total_seconds()
        if -5<delta<40:votes[closest['FCnt']-int(r['Tx Cnt'])]+=1
    assert len(votes)>=1;offset,support=votes.most_common()[0];assert support>votes.most_common()[1][1]*3
    offset_evidence.append(dict(File=file.name,ChosenOffset=offset,TemporalVotes=votes.most_common(8),Rule='Modo de offsets por proximidad temporal, verificado despues en toda la secuencia; no universal'))
    for i,r in enumerate(raw,1):
        t=dt.datetime.fromisoformat(r['Time']);tx=int(r['Tx Cnt']);counter=tx+offset;e=by_counter.get(counter)
        delta=(t-e['Time']).total_seconds() if e else math.nan
        assert not e or -5<delta<40,(file.name,tx,delta)
        gws={x['gateway_ids']['gateway_id']:x for x in e['Raw']['rx_metadata']} if e else {}
        assert set(gws)<=set(('gateway1','gateway2'))
        lat,lon=geo(r['Latitude']),geo(r['Longitude']);gps=math.isfinite(lat) and math.isfinite(lon)
        settings=e['Raw']['settings'] if e else {};rate=(settings.get('data_rate') or {}).get('lora',{})
        audited.append(dict(Campaign='C27-0810',Source_File=file.name,Source_Row=i,TrialKey=file.name+'|'+str(tx),Tx_Cnt=tx,Time_FT=str(t),In_declared_window='2026-10-27 08:10:00'<=str(t)<='2026-10-27 09:26:00',FCnt_offset=offset,Expected_FCnt=counter,TTS_received=bool(e),N_gateways=len(gws),gateway1_received='gateway1' in gws,gateway2_received='gateway2' in gws,Latitude=lat,Longitude=lon,GPS_valid=gps,FT_RSSI_dBm=num(r['RSSI (dBm)']),FT_SNR_dB=num(r['SNR (dB)']),SF_FT=r['SF'],TX_FT_declared=r['TX Power'],Time_TTS_radio_UTC=e['Raw']['settings']['time'] if e else '',Time_TTS_radio_local=e['Time'].replace(tzinfo=zone).isoformat() if e else '',FT_minus_radio_s=delta,TTS_SourceLine=e['SourceLine'] if e else '',SF_TTS=rate.get('spreading_factor'),BW_Hz=rate.get('bandwidth'),Frequency_Hz=settings.get('frequency'),**{gw+'_RSSI_dBm':gws.get(gw,{}).get('rssi') for gw in ('gateway1','gateway2')},**{gw+'_SNR_dB':gws.get(gw,{}).get('snr') for gw in ('gateway1','gateway2')}))
    ss=[r for r in audited if r['Source_File']==file.name]
    assert len({r['Expected_FCnt'] for r in ss})==len(ss)
    file_stats.append(dict(File=file.name,Rows=len(ss),First=ss[0]['Time_FT'],Last=ss[-1]['Time_FT'],GPS=sum(r['GPS_valid'] for r in ss),TTS=sum(r['TTS_received'] for r in ss),CounterGaps=sum(int(b['Tx_Cnt'])!=int(a['Tx_Cnt'])+1 for a,b in zip(ss,ss[1:]))))
assert len({r['Expected_FCnt'] for r in audited})==len(audited)
selected=[r for r in audited if r['In_declared_window']]
def summarize(rows):
    yes=[r for r in rows if r['TTS_received']];gps=[r for r in rows if r['GPS_valid']]
    return dict(Trials=len(rows),TTS_received=len(yes),NotFound=len(rows)-len(yes),StoredReception_pct=100*len(yes)/len(rows),GPS=len(gps),GPS_pct=100*len(gps)/len(rows),GPS_and_TTS=sum(r['GPS_valid'] and r['TTS_received'] for r in rows),GW1=sum(r['gateway1_received'] for r in rows),GW2=sum(r['gateway2_received'] for r in rows),Both=sum(r['N_gateways']==2 for r in rows),OnlyGW1=sum(r['gateway1_received'] and not r['gateway2_received'] for r in rows),OnlyGW2=sum(r['gateway2_received'] and not r['gateway1_received'] for r in rows),Median_FT_minus_radio_s=statistics.median(r['FT_minus_radio_s'] for r in yes),Min_FT_minus_radio_s=min(r['FT_minus_radio_s'] for r in yes),Max_FT_minus_radio_s=max(r['FT_minus_radio_s'] for r in yes),FT_RSSI_present=sum(math.isfinite(r['FT_RSSI_dBm']) for r in rows),FT_RSSI_missing_TTS_received=sum(not math.isfinite(r['FT_RSSI_dBm']) and r['TTS_received'] for r in rows),First=rows[0]['Time_FT'],Last=rows[-1]['Time_FT'],FirstGPS=gps[0]['Time_FT'] if gps else None,LastGPS=gps[-1]['Time_FT'] if gps else None)

nodes=read(FROZEN);node_by_id={int(n['Node_ID']):n for n in nodes};assert len(node_by_id)==len(nodes);lat=np.radians([num(n['Latitude']) for n in nodes]);lon=np.radians([num(n['Longitude']) for n in nodes]);associations=[];pairs=[];network=[];excursions=[]
valid=[r for r in selected if r['GPS_valid']]
for r in valid:
    a,b=map(math.radians,(r['Latitude'],r['Longitude']));dist=2*6371000*np.arcsin(np.minimum(1,np.sqrt(np.sin((lat-a)/2)**2+np.cos(lat)*math.cos(a)*np.sin((lon-b)/2)**2)))
    order=np.argsort(dist);i=int(order[0]);n=nodes[i];nid=int(n['Node_ID']);r['Node_ID']=nid;r['MatchDistance_m']=float(dist[i]);r['NearestMargin_m']=float(dist[order[1]]-dist[i]);r['Infrastructure']=nid<=2
    association=dict(**r,Primary_Street=n['Primary_Street'],Intersecting_Street=n['Intersecting_Street'],OutsideROI=hav((r['Latitude'],r['Longitude']),(-1.2516,-78.62772))>2800);associations.append(association)
    received=[]
    for gw,key in [('gateway1','RSSI_PALTAS_dBm'),('gateway2','RSSI_PUCESA_dBm')]:
        obs=num(r[gw+'_RSSI_dBm'])
        if math.isfinite(obs):
            pairs.append(dict(Node_ID=nid,TrialKey=r['TrialKey'],Gateway=gw,Distance_m=float(dist[i]),Observed=obs,Predicted=num(n[key]),Infrastructure=nid<=2))
            received.append(obs)
    if received:network.append(dict(Node_ID=nid,TrialKey=r['TrialKey'],Distance_m=float(dist[i]),obs=max(received),raw=max(num(n['RSSI_PUCESA_dBm']),num(n['RSSI_PALTAS_dBm'])),cal=num(n['Best_Predicted_RSSI_dBm']),Historical_RSSI=math.isfinite(num(n['Measured_Field_RSSI_dBm'])),Infrastructure=nid<=2))
for prev,r,nex in zip(valid,valid[1:],valid[2:]):
    ab=hav((prev['Latitude'],prev['Longitude']),(r['Latitude'],r['Longitude']));bc=hav((r['Latitude'],r['Longitude']),(nex['Latitude'],nex['Longitude']));ac=hav((prev['Latitude'],prev['Longitude']),(nex['Latitude'],nex['Longitude']))
    if ab>100 and bc>100 and ac<60:excursions.append(dict(TrialKey=r['TrialKey'],Time_FT=r['Time_FT'],Previous_m=ab,Next_m=bc,Bypass_m=ac))

results=[];aggregates=[];network45=[];pairs45=[]
for radius in (15,30,45,60):
    for label in ('gateway1','gateway2','network_raw','network_cal'):
        source=pairs if label.startswith('gateway') else network;ss=[p for p in source if not p['Infrastructure'] and p['Distance_m']<=radius and (not label.startswith('gateway') or p['Gateway']==label)]
        grouped=collections.defaultdict(list)
        for p in ss:grouped[p['Node_ID']].append(p)
        values=[]
        for nid,rows in grouped.items():
            pred=rows[0]['Predicted'] if label.startswith('gateway') else rows[0]['raw' if label=='network_raw' else 'cal'];obs=statistics.median(p['Observed'] if label.startswith('gateway') else p['obs'] for p in rows)
            val=dict(Node_ID=nid,Series=label,Radius_m=radius,Frames=len(rows),Predicted_dBm=pred,Observed_median_dBm=obs,Error_obs_minus_pred_dB=obs-pred,Median_match_m=statistics.median(p['Distance_m'] for p in rows),Historical_RSSI=math.isfinite(num(node_by_id[nid]['Measured_Field_RSSI_dBm'])))
            values.append(val)
        results.append(dict(Radius_m=radius,Series=label,Receptions=len(ss),**metrics([x['Predicted_dBm'] for x in values],[x['Observed_median_dBm'] for x in values])))
        if radius==45:
            aggregates.extend(values)
            if label=='network_cal':network45=values
            if label.startswith('gateway'):pairs45.extend(values)
for historical in (True,False):
    ss=[v for v in network45 if v['Historical_RSSI']==historical]
    results.append(dict(Radius_m=45,Series='network_cal_historical' if historical else 'network_cal_new_historical_locations',Receptions=sum(p['Frames'] for p in ss),**metrics([x['Predicted_dBm'] for x in ss],[x['Observed_median_dBm'] for x in ss])))
prior=read(args.prior_network);old103={int(r['Node_ID']) for r in prior};new={r['Node_ID'] for r in network45}
summary=dict(Campaign='C27-0810',DeclaredWindow='2026-10-27 08:10:00–09:26:00 UTC-05',Files=file_stats,AllRecords=summarize(audited),Declared=summarize(selected),OffsetEvidence=offset_evidence,NonTestMessages=non_test,SnapshotSHA256=manifest['raw_sha256'],FrozenDatasetSHA256=hashlib.sha256(FROZEN.read_bytes()).hexdigest(),AntennaIntervention='Investigador declara permanencia en parrilla, desplazamiento de antena y parada para reubicarla. Hora exacta no documentada; no se atribuye causalidad a la perdida GNSS.',GPS='No imputado ni reconstruido despues de ultima posicion',PotentialGPSExcursions=len(excursions),OutsideROI=sum(x['OutsideROI'] for x in associations),StreetCandidatesVisited45m=len({x['Node_ID'] for x in associations if x['Node_ID']>2 and x['MatchDistance_m']<=45}),StreetCandidatesWithSignal45m=len(new),OverlapWithC26_1400=len(new&old103),NewVsC26_1400=len(new-old103),UnionWithC26_1400=len(new|old103),Comparisons=results,Scope='Asociacion provisional por posicion FT; sin reajuste RF ni correccion temporal')
prior_dir=args.prior_network.parent.parent/'field_20261026'
if (prior_dir/'ensayos_ventanas_declaradas.csv').exists() and (prior_dir/'asociaciones_provisionales_intersecciones.csv').exists():
    keys={(x['Route'],x['Tx_Cnt']) for x in read(prior_dir/'ensayos_ventanas_declaradas.csv')}
    previous={int(x['Node_ID']) for x in read(prior_dir/'asociaciones_provisionales_intersecciones.csv') if (x['Route'],x['Tx_Cnt']) in keys and x['Within45m']=='True' and x['Infrastructure']=='False' and x['TTS_received']=='True'}
    summary.update(PriorThreeWindowsStreetCandidates=len(previous),NewVsThreeWindows=len(new-previous),UnionWithThreeWindows=len(new|previous))
write('ensayos_todos.csv',audited);write('ensayos_ventana_declarada.csv',selected);write('asociaciones_GPS.csv',associations);write('comparacion_senal.csv',results);write('medianas_candidatos_45m.csv',aggregates);write('network_cal_candidatos_45m.csv',network45);write('mensajes_fuera_patron.csv',non_test);write('posibles_excursiones_GPS.csv',excursions)
(OUT/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('Comparisons','OffsetEvidence')},ensure_ascii=False,indent=2));print('COMPARACIONES45',json.dumps([r for r in results if r['Radius_m']==45],ensure_ascii=False,indent=2))
if __name__=='__main__':pass
