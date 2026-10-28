from pathlib import Path
import json,csv,base64,math,statistics,collections
from datetime import datetime,timezone,timedelta
from auditar_cuatro_rutas import OUT,read,write,dist
snapshots=[Path('validacion_ruta2_20261026/extraccion_tts/20261026T200441Z/respuesta_original.jsonl'),OUT/'extraccion_tts/20261027T041849Z/respuesta_original.jsonl']
records={};reports=[]
for source in snapshots:
    for line_no,line in enumerate(source.read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip():continue
        if line.startswith('data:'):line=line[5:]
        d=json.loads(line).get('result');u=d.get('uplink_message',{});ids=d.get('end_device_ids',{})
        if ids.get('device_id')!='fieldtester':continue
        assert ids.get('dev_addr')=='27FAC2FF'
        counter=int(u['f_cnt']);raw=base64.b64decode(u.get('frm_payload',''));radio=u['settings'].get('time',d['received_at'])
        item=dict(counter=counter,radio=radio,server=d['received_at'],metadata=u.get('rx_metadata',[]),payload_hex=raw.hex(),Source=source.as_posix(),SourceLine=line_no)
        if raw!=b'\xff':reports.append({k:item[k] for k in ('counter','radio','server','payload_hex','Source','SourceLine')});continue
        assert counter not in records,'Contador repetido: revisar sesion antes de unir'
        records[counter]=item
offsets={'Ruta1':766,'Ruta2':1,'Ruta3':1108,'Ruta4':1057}
allrows=[];summary=[];rx=[]
for label,offset in offsets.items():
    rows=read(OUT/(label+'_filas_auditadas.csv'));joined=[]
    for row in rows:
        tx=int(float(row['Tx_Cnt']));counter=tx+offset;event=records.get(counter);gws={}
        if event:
            for m in event['metadata']:
                gw=m['gateway_ids']['gateway_id'];assert gw in ('gateway1','gateway2') and gw not in gws
                gws[gw]=m
            ft=datetime.fromisoformat(row['Time']).replace(tzinfo=timezone(timedelta(hours=-5)))
            radio=datetime.fromisoformat(event['radio'].replace('Z','+00:00'));delta=(ft-radio).total_seconds()
            assert -5<delta<40,('Tiempo incompatible con cruce',label,tx,delta)
        else:delta=None
        new=dict(Route=label,Row=int(row['Row']),Time_FT=row['Time'],Tx_Cnt=tx,Expected_FCnt=counter,FCnt_offset=offset,Latitude=row['Latitude'],Longitude=row['Longitude'],FT_RSSI_dBm=row['RSSI_dBm'],TTS_received=bool(event),N_gateways=len(gws),GW1_received='gateway1' in gws,GW2_received='gateway2' in gws,Time_TTS_radio=event['radio'] if event else None,FT_minus_radio_s=delta,TTS_source=event['Source'] if event else None,TTS_source_line=event['SourceLine'] if event else None,**{gw+'_RSSI_dBm':gws.get(gw,{}).get('rssi') for gw in ('gateway1','gateway2')})
        joined.append(new);allrows.append(new)
        if event:
            for gw,m in gws.items():rx.append(dict(Route=label,Tx_Cnt=tx,FCnt=counter,Gateway=gw,RSSI_dBm=m.get('rssi'),SNR_dB=m.get('snr'),AntennaIndex=m.get('antenna_index'),Time_TTS_radio=event['radio'],TTS_source=event['Source'],TTS_source_line=event['SourceLine']))
    scopes=[('whole_file',joined)]
    if label=='Ruta2':scopes.append(('since14_user_approx_movement',[r for r in joined if r['Time_FT']>='2026-10-26 14:00:00']))
    for scope,ss in scopes:
        summary.append(dict(Route=label,Scope=scope,Trials=len(ss),TTS_received=sum(r['TTS_received'] for r in ss),Not_found=sum(not r['TTS_received'] for r in ss),Stored_reception_pct=100*sum(r['TTS_received'] for r in ss)/len(ss),GW1=sum(r['GW1_received'] for r in ss),GW2=sum(r['GW2_received'] for r in ss),Both=sum(r['N_gateways']==2 for r in ss),OnlyGW1=sum(r['GW1_received'] and not r['GW2_received'] for r in ss),OnlyGW2=sum(r['GW2_received'] and not r['GW1_received'] for r in ss),Median_FT_minus_radio_s=statistics.median(r['FT_minus_radio_s'] for r in ss if r['TTS_received']),FT_RSSI_missing_but_TTS_received=sum(r['TTS_received'] and not math.isfinite(float(r['FT_RSSI_dBm'])) for r in ss),FT_RSSI_present_but_TTS_not_found=sum(not r['TTS_received'] and math.isfinite(float(r['FT_RSSI_dBm'])) for r in ss)))
    write(label+'_cruce_TTS.csv',joined)
write('recepciones_por_gateway.csv',rx);write('resumen_TTS.csv',summary);write('mensajes_no_patron_prueba.csv',reports)
(OUT/'resumen_TTS.json').write_text(json.dumps(dict(Summary=summary,Offsets=offsets,NonTestMessages=reports),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('RUTA4_BOUNDARY',json.dumps([dict(counter=key,**{k:records[key][k] for k in ('radio','payload_hex')}) for key in (1058,1107,1109)],indent=2))
