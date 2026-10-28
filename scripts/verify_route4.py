"""Comprobacion independiente, biblioteca estandar; no recalibra el modelo."""
from pathlib import Path
import json,csv,hashlib,math,re,base64,statistics,datetime as dt,collections
ROOT=Path(__file__).resolve().parents[1]
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def geo(s):
    m=re.fullmatch(r'\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*([NSEW])?\s*',s or '')
    return (-abs(float(m[1])) if m[2] in ('S','W') else float(m[1])) if m else math.nan
def distance(a,b):
    x,y,z,w=map(math.radians,(*a,*b));h=math.sin((z-x)/2)**2+math.cos(x)*math.cos(z)*math.sin((w-y)/2)**2
    return 12742000*math.asin(min(1,math.sqrt(h)))
def verify():
    data=ROOT/'data/field_20261027';meta=json.loads((data/'campaign_metadata.json').read_text(encoding='utf-8'))
    for item in meta['OriginalSources']:assert sha(data/item['File'])==item['SHA256']
    snapshot=next((data/'extraccion_tts').glob('*/respuesta_original.jsonl'));assert sha(snapshot)==meta['TTSSnapshotSHA256']
    manifest=json.loads((snapshot.parent/'manifest.json').read_text());assert manifest['http_status']==200 and manifest['parse_errors']==0 and not manifest['limit_reached']
    records=[];events={}
    for line in snapshot.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():continue
        d=json.loads(line.removeprefix('data:'))['result'];u=d['uplink_message'];records.append(d)
        assert d['end_device_ids']['device_id']=='fieldtester' and d['end_device_ids']['dev_addr']=='27FAC2FF'
        if base64.b64decode(u.get('frm_payload',''))!=b'\xff':continue
        assert u['f_cnt'] not in events
        events[u['f_cnt']]=u
    assert len(records)==385 and len(events)==383
    all_trials=rows(data/'resultados/ensayos_todos.csv');trials=rows(data/'resultados/ensayos_ventana_declarada.csv')
    assert len(all_trials)==483 and len(trials)==432 and sum(x['TTS_received']=='True' for x in trials)==332
    originals={}
    for item in meta['OriginalSources']:
        p=data/item['File']
        for r in rows(p):originals[(p.name,int(r['Tx Cnt']))]=r
    assert len(originals)==483
    offsets={'27octubreRuta4.1.csv':1316,'27octubreRuta4.2.csv':1713}
    for t in all_trials:
        original=originals[(t['Source_File'],int(t['Tx_Cnt']))];assert original['Time']==t['Time_FT']
        counter=int(t['Tx_Cnt'])+offsets[t['Source_File']];assert counter==int(t['Expected_FCnt'])
        event=events.get(counter);assert bool(event)==(t['TTS_received']=='True')
        if event:
            assert t['Time_TTS_radio_UTC']==event['settings']['time']
            assert dt.datetime.fromisoformat(t['Time_TTS_radio_local'])==dt.datetime.fromisoformat(event['settings']['time'].replace('Z','+00:00'))
            rx={x['gateway_ids']['gateway_id']:x for x in event['rx_metadata']};assert len(rx)==len(event['rx_metadata'])
            for gw in ('gateway1','gateway2'):
                if gw in rx:assert float(t[gw+'_RSSI_dBm'])==rx[gw]['rssi']
                else:assert t[gw+'_RSSI_dBm']==''
            radio=dt.datetime.fromisoformat(event['settings']['time'].replace('Z','+00:00')).astimezone(dt.timezone(dt.timedelta(hours=-5))).replace(tzinfo=None)
            delta=(dt.datetime.fromisoformat(t['Time_FT'])-radio).total_seconds();assert abs(delta-float(t['FT_minus_radio_s']))<1e-8
        for name in ('Latitude','Longitude'):
            a,b=geo(original[name]),float(t[name]);assert (math.isnan(a) and math.isnan(b)) or a==b
    selected=[r for r in all_trials if '2026-10-27 08:10:00'<=r['Time_FT']<='2026-10-27 09:26:00'];assert selected==trials
    gps=[r for r in trials if r['GPS_valid']=='True'];assert len(gps)==181 and gps[-1]['Time_FT']=='2026-10-27 08:41:51'
    assert sum(x['gateway1_received']=='True' for x in trials)==256 and sum(x['gateway2_received']=='True' for x in trials)==211
    assert sum(x['N_gateways']=='2' for x in trials)==135
    frozen=ROOT/'src/matlab/datos/nodos_referencia.csv';assert sha(frozen)==meta['FrozenDatasetSHA256']
    nodes=rows(frozen);by_id={int(n['Node_ID']):n for n in nodes};assert len(nodes)==2630
    associations={r['TrialKey']:r for r in rows(data/'resultados/asociaciones_GPS.csv')};observed=collections.defaultdict(list)
    for r in gps:
        pos=(float(r['Latitude']),float(r['Longitude']));d,n=min((distance(pos,(float(n['Latitude']),float(n['Longitude']))),int(n['Node_ID'])) for n in nodes)
        a=associations[r['TrialKey']];assert n==int(a['Node_ID']) and abs(d-float(a['MatchDistance_m']))<1e-6
        signals=[float(r[gw+'_RSSI_dBm']) for gw in ('gateway1','gateway2') if r[gw+'_RSSI_dBm']!='']
        if n>2 and d<=45 and signals:observed[n].append(max(signals))
    assert len(observed)==35 and sum(map(len,observed.values()))==69
    saved={int(r['Node_ID']):r for r in rows(data/'resultados/network_cal_candidatos_45m.csv')};errors=[];raw_errors=[]
    for n,values in observed.items():
        obs=statistics.median(values);pred=float(by_id[n]['Best_Predicted_RSSI_dBm']);assert obs==float(saved[n]['Observed_median_dBm']) and pred==float(saved[n]['Predicted_dBm'])
        errors.append(obs-pred);raw_errors.append(obs-max(float(by_id[n]['RSSI_PUCESA_dBm']),float(by_id[n]['RSSI_PALTAS_dBm'])))
    rmse=math.sqrt(sum(e*e for e in errors)/len(errors));raw_rmse=math.sqrt(sum(e*e for e in raw_errors)/len(raw_errors))
    assert abs(rmse-23.8523673577997)<1e-10 and abs(raw_rmse-22.14770545999872)<1e-10
    assert sum(abs(e)<=6 for e in errors)==1
    return dict(Status='PASS',Campaign='C27-0810',Trials=432,TTSReceived=332,GPS=181,StreetCandidates=35,CalibratedFrozenRMSE_dB=rmse,RawBestRMSE_dB=raw_rmse,Within6_Count=1,Scope='Radio verificable; contraste espacial parcial sin imputacion GNSS ni recalibracion')
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
