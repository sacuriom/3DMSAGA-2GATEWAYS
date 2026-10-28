"""Extract TTS Storage without executing received scripts or recording credentials.

Live: python extraer_tts_verificable.py --fetch --key-source PATH
Offline: python extraer_tts_verificable.py --input-jsonl RESPONSE
Credentials: TTS_API_KEY environment variable, or a literal API_KEY read with ast.
"""
from pathlib import Path
import argparse, ast, csv, datetime as dt, hashlib, json, os, re, urllib.request, urllib.parse, urllib.error

def parse_line(line):
    line=line.strip()
    if not line or line.startswith((':','event:','id:','retry:')):return None
    if line.startswith('data:'):line=line[5:].strip()
    return json.loads(line)

def extract(objects):
    receptions=[];messages=[]
    for o in objects:
        obj=o.get('result',o)
        up=obj.get('uplink_message')
        if not isinstance(up,dict):continue
        ids=obj.get('end_device_ids',{});device=ids.get('device_id','');session=up.get('session_key_id','')
        received=obj.get('received_at') or up.get('received_at','');fcnt=up.get('f_cnt')
        identity=dict(device=device,session=session,fcnt=fcnt,received_at=received,payload=up.get('frm_payload',''))
        uid=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        decoded=up.get('decoded_payload') or {};locations=up.get('locations') or {}
        lat=decoded.get('latitude');lon=decoded.get('longitude');gps_source='decoded_payload'
        if lat is None or lon is None:
            loc=locations.get('user') or {};lat=loc.get('latitude');lon=loc.get('longitude');gps_source='user_location'
        if lat is None or lon is None:gps_source='not_available'
        settings=up.get('settings') or {};rate=(settings.get('data_rate') or {}).get('lora') or {}
        metadata=up.get('rx_metadata') or [];gateways=sorted(set(r.get('gateway_ids',{}).get('gateway_id','') for r in metadata)-{''})
        common=dict(Message_ID=uid,Timestamp=received,Device_ID=device,Dev_Addr=ids.get('dev_addr',''),Session_Key_ID=session,FCnt=fcnt,FPort=up.get('f_port'),Latitude=lat,Longitude=lon,Location_Source=gps_source,Frequency_Hz=settings.get('frequency'),SF=rate.get('spreading_factor'),BW_Hz=rate.get('bandwidth'),Coding_Rate=rate.get('coding_rate') or settings.get('coding_rate'))
        messages.append(dict(**common,Distinct_Gateways=len(gateways),Gateway_IDs=';'.join(gateways),Metadata_Entries=len(metadata)))
        for rx in metadata:
            loc=rx.get('location') or {}
            receptions.append(dict(**common,Gateway_ID=rx.get('gateway_ids',{}).get('gateway_id',''),Antenna_Index=rx.get('antenna_index'),RSSI_dBm=rx.get('rssi'),Signal_RSSI_dBm=rx.get('signal_rssi'),SNR_dB=rx.get('snr'),Gateway_Received_At=rx.get('received_at'),Gateway_Time=rx.get('time'),Gateway_Latitude=loc.get('latitude'),Gateway_Longitude=loc.get('longitude')))
    return messages,receptions

def write_csv(p,rows):
    if not rows:return
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)

def get_key(source):
    key=os.environ.get('TTS_API_KEY')
    if key:return key
    if source:
        text=Path(source).read_text(encoding='utf-8-sig')
        if Path(source).suffix.lower()=='.m':
            found=re.search(r"TTS_Config\.APIKey\s*=\s*'([^']+)'",text)
            if found:return found[1]
        tree=ast.parse(text)
        for n in ast.walk(tree):
            if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):
                if any(isinstance(t,ast.Name) and t.id=='API_KEY' for t in n.targets):return n.value.value
    raise ValueError('Falta TTS_API_KEY o un archivo con API_KEY literal. No se ejecuta el archivo recibido.')

def main():
    a=argparse.ArgumentParser();mode=a.add_mutually_exclusive_group(required=True)
    mode.add_argument('--fetch',action='store_true');mode.add_argument('--input-jsonl',type=Path)
    a.add_argument('--key-source',type=Path);a.add_argument('--app-id',default='field-tester-ambato')
    a.add_argument('--normalize-prefix',action='store_true',help='Remove a single extraneous T before the documented NNSXS prefix')
    a.add_argument('--host',default='coberturaiotambato.nam1.cloud.thethings.industries')
    a.add_argument('--after',default='2026-10-01T00:00:00Z');a.add_argument('--limit',type=int,default=1000)
    a.add_argument('--output',type=Path,default=Path('tts_extraccion_directa'))
    args=a.parse_args();stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=args.output/stamp;out.mkdir(parents=True,exist_ok=False)
    (out/'extractor_snapshot.py').write_bytes(Path(__file__).read_bytes())
    manifest=dict(extracted_at_utc=stamp,source='live_tts_api' if args.fetch else 'offline_response',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    raw=out/'respuesta_original.jsonl'
    if args.fetch:
        key=get_key(args.key_source)
        if args.normalize_prefix and key.startswith('TNNSXS.'):
            key=key[1:];manifest['credential_prefix_correction']='Removed single extra character before documented token type'
        host=args.host
        if '/' in host or ':' in host:raise ValueError('Host inválido')
        endpoint='https://'+host+'/api/v3/as/applications/'+urllib.parse.quote(args.app_id,safe='')+'/packages/storage/uplink_message'
        params=dict(limit=args.limit)
        if args.after:params['after']=args.after
        query=urllib.parse.urlencode(params)
        manifest.update(endpoint=endpoint,after=args.after,requested_limit=args.limit)
        request=urllib.request.Request(endpoint+'?'+query,headers={'Authorization':'Bearer '+key,'Accept':'text/event-stream'})
        try:
            with urllib.request.urlopen(request,timeout=60) as response,raw.open('wb') as f:
                manifest['http_status']=response.status;manifest['content_type']=response.headers.get('Content-Type')
                while True:
                    block=response.read(65536)
                    if not block:break
                    f.write(block)
        except urllib.error.HTTPError as e:
            manifest.update(http_status=e.code,error='HTTP error; credenciales y respuesta de error no publicadas')
            body=e.read().decode('utf-8',errors='replace').replace(key,'CREDENCIAL_RETIRADA')
            try:
                err=json.loads(body)
                if isinstance(err.get('error'),dict):err=err['error']
                manifest['server_error']={k:err[k] for k in ('code','message','details') if k in err}
                if not manifest['server_error']:manifest['server_error']={'fields':list(err)[:10]}
            except json.JSONDecodeError:manifest['server_error']='Respuesta no JSON'
            (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            print(json.dumps(manifest));return 2
        except urllib.error.URLError as e:
            manifest.update(error_type=type(e.reason).__name__,error='No se obtuvo respuesta de TTS')
            (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            print(json.dumps(manifest));return 3
    else:raw.write_bytes(args.input_jsonl.read_bytes())
    objects=[];parse_errors=0
    for line in raw.read_text(encoding='utf-8-sig').splitlines():
        try:
            obj=parse_line(line)
            if isinstance(obj,dict):objects.append(obj)
        except json.JSONDecodeError:parse_errors+=1
    messages,receptions=extract(objects)
    write_csv(out/'mensajes_tts.csv',messages);write_csv(out/'recepciones_gateway_tts.csv',receptions)
    distinct={r['Message_ID']:r for r in messages}
    manifest.update(raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),response_objects=len(objects),parse_errors=parse_errors,message_rows=len(messages),distinct_message_records=len(distinct),reception_rows=len(receptions),messages_with_two_or_more_gateways=sum(r['Distinct_Gateways']>=2 for r in distinct.values()),gateway_ids=sorted(set(r['Gateway_ID'] for r in receptions)),limit_reached=bool(args.fetch and len(objects)>=args.limit),scope='Received messages only; not a PDR denominator. Message_ID identifies a server record, not all retransmissions of an application message.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(output=str(out.resolve()),**manifest),ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
