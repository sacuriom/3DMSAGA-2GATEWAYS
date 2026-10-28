from pathlib import Path
import csv,re,math,json,hashlib,shutil,collections,statistics
from datetime import datetime
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'auditoria_cuatro_rutas_20261026';OUT.mkdir(exist_ok=True)
FILES=[('Ruta1','26octRuta1.csv'),('Ruta2','26octRuta2Test (1).csv'),('Ruta3','26octTuta3.csv'),('Ruta4','26octRura4(amla).csv')]
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def number(s):
    try:return float(s)
    except (ValueError,TypeError):return math.nan
def geo(s):
    m=re.fullmatch(r'\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*([NSEW])?\s*',s or '')
    if not m:return math.nan
    return -abs(float(m[1])) if m[2] in ('S','W') else float(m[1])
def dist(a,b):
    if not all(math.isfinite(v) for v in (*a,*b)):return math.nan
    x=math.radians(b[1]-a[1])*6371000*math.cos(math.radians((a[0]+b[0])/2));y=math.radians(b[0]-a[0])*6371000
    return math.hypot(x,y)
def write(name,rows):
    if not rows:return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def percentile(vals,p):
    vals=sorted(v for v in vals if math.isfinite(v));i=(len(vals)-1)*p
    return vals[math.floor(i)]*(math.ceil(i)-i)+vals[math.ceil(i)]*(i-math.floor(i)) if vals and i%1 else vals[int(i)] if vals else None
def analyze(label,path):
    original=read(path)
    if path.resolve()!=(OUT/(label+'_original.csv')).resolve():shutil.copyfile(path,OUT/(label+'_original.csv'))
    rows=[];alerts=[]
    for i,r in enumerate(original):
        t=datetime.strptime(r['Time'],'%Y-%m-%d %H:%M:%S');lat=geo(r['Latitude']);lon=geo(r['Longitude']);rssi=number(r['RSSI (dBm)']);snr=number(r['SNR (dB)']);tx=number(r['Tx Cnt']);ack=number(r['Confirm Packet']);uplink=number(r['UPlink Packet']);gps=math.isfinite(lat) and math.isfinite(lon)
        rr=dict(Route=label,Row=i+1,Time=r['Time'],Tx_Cnt=tx,Uplink= uplink,Confirm=ack,Latitude=lat,Longitude=lon,RSSI_dBm=rssi,SNR_dB=snr,Signal=r['Signal'],SF=r['SF'],Power=r['TX Power'],GPS_valid=gps,dt_s=None,Tx_delta=None,Confirm_delta=None,Step_m=None,Implied_kmh=None)
        if rows:
            prev=rows[-1];dt=(t-datetime.fromisoformat(prev['Time'])).total_seconds();step=dist((prev['Latitude'],prev['Longitude']),(lat,lon));rr.update(dt_s=dt,Tx_delta=tx-prev['Tx_Cnt'],Confirm_delta=ack-prev['Confirm'],Step_m=step,Implied_kmh=step/dt*3.6 if dt>0 else None)
            kinds=[]
            if dt>30:kinds.append('time_gap_over30s')
            if dt<=0:kinds.append('non_increasing_time')
            if rr['Tx_delta']!=1:kinds.append('nonunit_tx_counter')
            if rr['Confirm_delta']<0:kinds.append('confirm_reset')
            if rr['Implied_kmh'] is not None and rr['Implied_kmh']>120:kinds.append('gps_implied_over120kmh')
            for kind in kinds:alerts.append(dict(Route=label,Issue=kind,**{k:rr[k] for k in ('Row','Time','dt_s','Tx_Cnt','Tx_delta','Confirm_delta','Step_m','Implied_kmh')}))
        rows.append(rr)
    # No se deduce movimiento real solo de posiciones GNSS.
    def summary(ss,scope):
        times=[datetime.fromisoformat(r['Time']) for r in ss];delta=[(b-a).total_seconds() for a,b in zip(times,times[1:])];gps=[r for r in ss if r['GPS_valid']];rss=[r['RSSI_dBm'] for r in ss if math.isfinite(r['RSSI_dBm'])];span=(times[-1]-times[0]).total_seconds();steps=[dist((a['Latitude'],a['Longitude']),(b['Latitude'],b['Longitude'])) for a,b in zip(ss,ss[1:])];cells={(math.floor(r['Longitude']*111195*math.cos(math.radians(-1.26))/100),math.floor(r['Latitude']*111195/100)) for r in gps}
        return dict(Route=label,Scope=scope,Rows=len(ss),Start=ss[0]['Time'],End=ss[-1]['Time'],Duration_min=span/60,Tx_first=ss[0]['Tx_Cnt'],Tx_last=ss[-1]['Tx_Cnt'],Tx_counter_span=ss[-1]['Tx_Cnt']-ss[0]['Tx_Cnt']+1,Tx_nonunit_transitions=sum(b['Tx_Cnt']-a['Tx_Cnt']!=1 for a,b in zip(ss,ss[1:])),Median_interval_s=statistics.median(delta) if delta else None,Max_interval_s=max(delta) if delta else None,Time_gaps_gt30s=sum(x>30 for x in delta),RSSI_rows=len(rss),RSSI_available_pct=100*len(rss)/len(ss),GPS_rows=len(gps),GPS_available_pct=100*len(gps)/len(ss),Unique_GPS=len({(r['Latitude'],r['Longitude']) for r in gps}),Grid100m_cells=len(cells),GPS_polyline_km=sum(x for x in steps if math.isfinite(x))/1000,Steps_gt120kmh=sum(math.isfinite(step) and dt>0 and step/dt*3.6>120 for step,dt in zip(steps,delta)),Confirm_first=ss[0]['Confirm'],Confirm_last=ss[-1]['Confirm'],Confirm_nonunit_transitions=sum(b['Confirm']-a['Confirm'] not in (0,1) for a,b in zip(ss,ss[1:])),Confirm_final_over_Tx_final_pct=100*ss[-1]['Confirm']/ss[-1]['Tx_Cnt'],RSSI_median=statistics.median(rss) if rss else None,Missing_RSSI_longest_run=max((len(list(g)) for k,g in __import__('itertools').groupby(ss,key=lambda r:not math.isfinite(r['RSSI_dBm'])) if k),default=0),SF=dict(collections.Counter(r['SF'] for r in ss)),Power=dict(collections.Counter(r['Power'] for r in ss)),Signal=dict(collections.Counter(r['Signal'] for r in ss)),Latitude_range=[min(r['Latitude'] for r in gps),max(r['Latitude'] for r in gps)] if gps else None,Longitude_range=[min(r['Longitude'] for r in gps),max(r['Longitude'] for r in gps)] if gps else None)
    stats=[summary(rows,'whole_file')]
    if label=='Ruta2':stats.append(summary([r for r in rows if r['Time']>='2026-10-26 14:00:00'],'since14_user_approx_movement'))
    bins=collections.defaultdict(list)
    for r in rows:bins[r['Time'][:15]+'0:00'].append(r)
    tenmin=[]
    for key,ss in bins.items():tenmin.append(dict(Route=label,TenMinute=key,Rows=len(ss),RSSI_rows=sum(math.isfinite(r['RSSI_dBm']) for r in ss),GPS_rows=sum(r['GPS_valid'] for r in ss)))
    write(label+'_filas_auditadas.csv',rows)
    return stats,alerts,tenmin,rows,dict(Route=label,Input=str(path),SHA256=hashlib.sha256(path.read_bytes()).hexdigest(),Bytes=path.stat().st_size)

if __name__=='__main__':
    allstats=[];alerts=[];bins=[];normalized=[];sources=[]
    for label,name in FILES:
        path=Path('C:/Users/sacur/AppData/Local/Temp')/name
        if not path.exists():path=OUT/(label+'_original.csv')
        stats,a,b,rows,source=analyze(label,path);allstats+=stats;alerts+=a;bins+=b;normalized+=rows;sources.append(source)
    write('resumen_rutas.csv',allstats);write('alertas.csv',alerts);write('registros_por_10min.csv',bins)
    (OUT/'resumen.json').write_text(json.dumps(dict(Routes=allstats,Sources=sources),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(allstats,ensure_ascii=False,indent=2))
