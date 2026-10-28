"""Verifica campos de observacion contra los snapshots TTS sin tokens."""
from pathlib import Path
import csv,json,base64,hashlib,math,collections,re
ROOT=Path(__file__).resolve().parents[1]
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    trace=json.loads((ROOT/'provenance/redactions.json').read_text(encoding='utf-8'))
    events={};all_events=[]
    for item in trace['Transformations']:
        p=ROOT/item['PublishedFile'];assert sha(p)==item['PublishedSHA256']
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():continue
            data=json.loads(line)['result'];up=data['uplink_message'];all_events.append(up)
            if base64.b64decode(up.get('frm_payload',''))!=b'\xff':continue
            assert data['end_device_ids']['device_id']=='fieldtester'
            key=int(up['f_cnt']);assert key not in events,'Revisar sesion: contador ambiguo'
            events[key]=up
    observations=rows(ROOT/'data/field_20261026/ensayos_ventanas_declaradas.csv');assert len(observations)==670
    assert len({(r['Declared_Route'],r['Tx_Cnt']) for r in observations})==670
    originals=json.loads((ROOT/'provenance/field_originals.json').read_text(encoding='utf-8'))
    for item in originals['Files']:assert sha(ROOT/item['File'])==item['SHA256']
    windows={'Ruta 1':('26octRuta2Test (1).csv','14:00:00','15:10:00',1),'Ruta 2':('26octRuta1.csv','16:20:00','17:00:00',766),'Ruta 3':('26octTuta3.csv','21:38:00','22:04:00',1108)}
    def geo(value):
        m=re.fullmatch(r'\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*([NSEW])?\s*',value or '')
        return (-abs(float(m[1])) if m[2] in ('S','W') else float(m[1])) if m else math.nan
    for route,(name,start,end,offset) in windows.items():
        raw=rows(ROOT/'data/field_20261026/ft_originals'/name)
        selected=[r for r in raw if '2026-10-26 '+start<=r['Time']<='2026-10-26 '+end]
        declared=[r for r in observations if r['Declared_Route']==route]
        assert len(selected)==len(declared)
        for original,observation in zip(selected,declared):
            assert int(original['Tx Cnt'])==int(observation['Tx_Cnt']) and original['Time']==observation['Time_FT']
            assert int(observation['Expected_FCnt'])==int(original['Tx Cnt'])+offset
            for name in ('Latitude','Longitude'):
                a,b=geo(original[name]),float(observation[name])
                assert (math.isnan(a) and math.isnan(b)) or a==b
    counts=collections.defaultdict(lambda:[0,0])
    for r in observations:
        event=events.get(int(r['Expected_FCnt']));assert bool(event)==(r['TTS_received']=='True')
        counts[r['Declared_Route']][0]+=1;counts[r['Declared_Route']][1]+=bool(event)
        if event:
            receivers={m['gateway_ids']['gateway_id']:m for m in event['rx_metadata']}
            for gw in ('gateway1','gateway2'):
                value=r[gw+'_RSSI_dBm']
                if gw in receivers:assert float(value)==receivers[gw]['rssi']
                else:assert value==''
    assert dict(counts)=={'Ruta 1':[291,267],'Ruta 2':[231,134],'Ruta 3':[148,103]}
    absent=[u for u in all_events if '2026-10-27T03:08:00'<=u['settings']['time'][:19]<='2026-10-27T04:00:00']
    assert not absent,'Se requiere actualizar el resultado de Ruta 4'
    values=rows(ROOT/'data/field_model_comparison/red_mejor_enlace_intersecciones_sin_anclas.csv')
    errors=[float(r['obs'])-float(r['cal']) for r in values]
    rmse=math.sqrt(sum(e*e for e in errors)/len(errors));assert len(errors)==103 and abs(rmse-11.764699543116508)<1e-10
    for item in json.loads((ROOT/'src/matlab/datos/manifest_entradas.json').read_text())['Files']:
        assert sha(ROOT/'src/matlab/datos'/item['Name'])==item['SHA256']
    provenance=json.loads((ROOT/'src/matlab/datos/trazabilidad_fuentes.json').read_text(encoding='utf-8'))
    for item in provenance['Files']:assert sha(ROOT/'src/matlab/fuentes'/item['Name'])==item['SHA256']
    from verify_route4 import verify
    repeated=verify()
    print(json.dumps(dict(Status='PASS',Scope='Auditoria de snapshots preparados para difusion; asociacion espacial provisional',DeclaredWindows=dict(counts),Route4Original='Sin CSV ni denominador; cero mensajes observados en la ventana original',FrozenCalibratedNetworkRMSE_dB=rmse,RepeatedRoute4=repeated),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
