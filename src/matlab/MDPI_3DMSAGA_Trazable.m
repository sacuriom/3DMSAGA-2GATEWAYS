function out = MDPI_3DMSAGA_Trazable(C)
% Auditoria y escenario RF separados. No consulta la API ni modifica originales.
% Requiere las entradas congeladas con manifest_entradas.json.
if nargin == 0, C = config_campana_ambato(); end
assert(C.Role == "evaluation", 'Trazable:Role', ...
    'Esta funcion evalua; use otro conjunto explicitamente para ajustar.');
assert(C.ClockCorrection_s == 0, 'Trazable:Clock', ...
    'No esta implementada una correccion temporal sin traza GNSS sincronizada.');
assert(C.ExcludeInfrastructureFromMetrics, 'Trazable:Infrastructure', ...
    'Las metricas de calle deben excluir las anclas.');
verify_inputs(C.InputRoot);
sourceDefinition=jsondecode(fileread(fullfile(C.InputRoot,'trazabilidad_fuentes.json')));
assert(C.CampaignID==string(sourceDefinition.CampaignID), ...
    'Trazable:CampaignIdentity','La configuracion no corresponde a la campana de los archivos.');
T = readtable(fullfile(C.InputRoot,'nodos_referencia.csv'), 'TextType','string');
F = readtable(fullfile(C.InputRoot,'ensayos.csv'), 'TextType','string');
R = readtable(fullfile(C.InputRoot,'recepciones.csv'), 'TextType','string');
assert(height(T)>=2 && height(F)>0 && height(R)>0,'Trazable:Empty', ...
    'Sin ensayos o recepciones no se puede evaluar la concordancia de RSSI.');
assert(numel(unique(T.Node_ID)) == height(T),'Trazable:NodeID','IDs repetidos.');
assert(numel(unique(F.TrialKey)) == height(F),'Trazable:TrialID','Ensayos repetidos.');
assert(all(isfinite(F.Latitude) & isfinite(F.Longitude)), ...
    'Trazable:GPS','Esta cohorte requiere coordenadas FT finitas.');
assert(all(F.Latitude>=-2 & F.Latitude<=-0.5 & F.Longitude>=-79.5 & F.Longitude<=-78), ...
    'Trazable:GPS','Coordenadas fuera del entorno; no se invierten signos.');
assert(all(ismember(R.Gateway_ID,string({C.Gateways.ID}))), ...
    'Trazable:Gateway','Gateway no identificado: no asignar uno por defecto.');
assert(all(R.SF==9 & R.Bandwidth_Hz==125000), ...
    'Trazable:Radio','La cohorte no es homogenea SF9/BW125.');
assert(all(isfinite(R.RSSI_dBm) & isfinite(R.Frequency_Hz)), ...
    'Trazable:Reception','Recepciones sin RSSI o frecuencia verificable.');
[ok, fi] = ismember(R.TrialKey,F.TrialKey);
assert(all(ok), 'Trazable:Join','Recepcion sin ensayo identificado.');
assert(all(double(F.TTS_received)==double(ismember(F.TrialKey,R.TrialKey))), ...
    'Trazable:Join','Inconsistencia en ensayos recibidos.');
key = R.TrialKey+"|"+R.Gateway_ID;
assert(numel(unique(key))==height(R),'Trazable:Duplicate', ...
    'Hay varios metadatos por ensayo y gateway; definir politica por antena.');

origin = [mean(T.Latitude),mean(T.Longitude)];
[x,y] = local_xy(T.Latitude,T.Longitude,origin);
[fx,fy] = local_xy(F.Latitude,F.Longitude,origin);
row = zeros(height(F),1); d1 = row; d2 = row;
for k=1:height(F)
    distances = hypot(x-fx(k),y-fy(k)); [sorted,idx] = sort(distances);
    row(k)=idx(1); d1(k)=sorted(1); d2(k)=sorted(2);
end
F.Node_ID = T.Node_ID(row); F.NodeRow = row;
F.MatchDistance_m = d1; F.SecondDistance_m = d2;
F.NearestMargin_m = d2-d1;
F.AmbiguousNeighbour = F.NearestMargin_m < C.AmbiguityMargin_m;
F.Infrastructure = ismember(F.Node_ID,[C.Gateways.NodeID]);
F.TimePositionSemanticsVerified = repmat(C.TimePositionSemanticsVerified,height(F),1);
F.GNSSAccuracyVerified = repmat(C.GNSSAccuracyVerified,height(F),1);
R.Node_ID=F.Node_ID(fi); R.NodeRow=row(fi);
R.MatchDistance_m=d1(fi); R.Infrastructure=F.Infrastructure(fi);
R.Primary_Street=T.Primary_Street(row(fi));
R.Intersecting_Street=T.Intersecting_Street(row(fi));
R.GatewayIndex=zeros(height(R),1);
for k=1:numel(C.Gateways), R.GatewayIndex(R.Gateway_ID==C.Gateways(k).ID)=k; end

matrix = []; bin = []; points = []; ground = [];
if C.Mode == "legacy_audit"
    assert(strlength(C.CalibrationFile)==0,'Trazable:Calibration', ...
        'No aplicar nuevos coeficientes al historico durante su auditoria.');
    assert(~C.RunBenchmark,'Trazable:Benchmark', ...
        'El CSV heredado solo contiene dos columnas RF; no una matriz completa.');
    pred=[T.RSSI_PUCESA_dBm,T.RSSI_PALTAS_dBm];
    bestLegacyCal=T.Best_Predicted_RSSI_dBm;
    modelLabel="legacy_raw_27dBm_915MHz_unverified_heights";
    threshold=C.Model.LegacyThreshold_dBm;
elseif C.Mode == "physical_model"
    [matrix,bin,points,ground,C] = RF_uplink_trazable(T,C,R);
    [found,anchorRows]=ismember([C.Gateways.NodeID],T.Node_ID);
    assert(all(found),'Trazable:Anchor','Ancla sin ID de nodo.');
    pred=matrix(:,anchorRows); bestLegacyCal=nan(height(T),1);
    modelLabel=C.Model.Version; threshold=C.Model.Sensitivity_dBm;
else
    error('Trazable:Mode','Modo no reconocido.');
end
signature=struct('Model',C.Model,'Gateways',C.Gateways, ...
    'NodeSourceSHA256',sha256_file(fullfile(C.InputRoot,'nodos_referencia.csv')));
if C.Mode=="physical_model"
    signature.GroundSourceSHA256=sha256_file(C.Model.GroundElevationCSV);
    signature.ImplementationSHA256=sha256_file(which('RF_uplink_trazable'));
end
C.ModelFingerprintSHA256=sha256_text(jsonencode(signature));
R.PredictedRaw_dBm=pred(sub2ind(size(pred),row(fi),R.GatewayIndex));
if C.Mode == "physical_model"
    R.PredictedRaw_dBm=R.PredictedRaw_dBm ...
        -20*log10((R.Frequency_Hz/1e6)/C.Model.ReferenceFrequencyMHz);
end
R.PredictedCalibrated_dBm=nan(height(R),1);
if strlength(C.CalibrationFile)>0
    assert(~C.RunBenchmark,'Trazable:Transfer', ...
        'Una correccion de dos gateways no se transfiere a sitios hipoteticos.');
    coefficients=jsondecode(fileread(C.CalibrationFile));
    assert(string(coefficients.BaseModelVersion)==C.Model.Version, ...
        'Trazable:CalibrationVersion','Modelo y coeficientes incompatibles.');
    assert(string(coefficients.BaseModelSHA256)==C.ModelFingerprintSHA256, ...
        'Trazable:CalibrationFingerprint','Han cambiado condiciones o implementacion del modelo calibrado.');
    assert(string(coefficients.DeclaredRole)=="training", ...
        'Trazable:CalibrationRole','El ajuste debe declarar su conjunto de entrenamiento.');
    assert(string(coefficients.CampaignID)~=C.CampaignID, ...
        'Trazable:Leakage','Calibracion y evaluacion comparten campana.');
    trainingKeys=string(coefficients.TrainingFrameKeys);
    assert(~any(ismember(R.FrameKey,trainingKeys)), ...
        'Trazable:Leakage','Una trama de evaluacion aparece en entrenamiento.');
    for k=1:numel(C.Gateways)
        q=find(string({coefficients.Gateways.ID})==C.Gateways(k).ID);
        assert(isscalar(q),'Trazable:CalibrationGateway','Falta un receptor calibrado.');
        g=coefficients.Gateways(q);
        assert(g.Slope==1,'Trazable:CalibrationSlope', ...
            'Este flujo solo admite correccion de offset, sin comprimir amplitud.');
        v=R.GatewayIndex==k;
        R.PredictedCalibrated_dBm(v)=R.PredictedRaw_dBm(v)+g.Offset_dB;
        pred(:,k)=pred(:,k)+g.Offset_dB;
    end
end
R.ResidualRaw_dB=R.RSSI_dBm-R.PredictedRaw_dBm;
R.ResidualCalibrated_dB=R.RSSI_dBm-R.PredictedCalibrated_dBm;
% No poner RSSI ficticio a los ensayos no recibidos.
F.BestReceived_dBm=nan(height(F),1);
F.BestPredictedRaw_dBm=nan(height(F),1);
F.BestPredictedCalibrated_dBm=nan(height(F),1);
for k=1:height(F)
    rr=find(fi==k);
    if isempty(rr),continue;end
    F.BestReceived_dBm(k)=max(R.RSSI_dBm(rr));
    F.BestPredictedRaw_dBm(k)=max(pred(row(k),:));
    if C.Mode=="legacy_audit"
        F.BestPredictedCalibrated_dBm(k)=bestLegacyCal(row(k));
    else
        correction=-20*log10((R.Frequency_Hz(rr(1))/1e6)/C.Model.ReferenceFrequencyMHz);
        F.BestPredictedRaw_dBm(k)=max(matrix(row(k),anchorRows))+correction;
        if strlength(C.CalibrationFile)>0
            F.BestPredictedCalibrated_dBm(k)=max(pred(row(k),:))+correction;
        end
    end
end

allMetrics=table(); primaryLinks=table(); primaryNetwork=table();
for radius=C.MatchRadii_m
    eligible=R.MatchDistance_m<=radius & ~R.Infrastructure;
    links=aggregate_links(R(eligible,:),C.CampaignID,modelLabel,C.ModelFingerprintSHA256);
    network=aggregate_network(F(F.MatchDistance_m<=radius & ~F.Infrastructure,:),T);
    if radius==C.PrimaryRadius_m,primaryLinks=links;primaryNetwork=network;end
    for k=1:numel(C.Gateways)
        sel=links.Gateway_ID==C.Gateways(k).ID;
        allMetrics=[allMetrics;metric_row(radius,C.Gateways(k).ID+"_raw", ...
            links.PredictedRaw_dBm(sel),links.MeasuredMedian_dBm(sel))]; %#ok<AGROW>
        if strlength(C.CalibrationFile)>0
            allMetrics=[allMetrics;metric_row(radius,C.Gateways(k).ID+"_calibrated", ...
                links.PredictedCalibrated_dBm(sel),links.MeasuredMedian_dBm(sel))]; %#ok<AGROW>
        end
    end
    allMetrics=[allMetrics;metric_row(radius,"network_best_raw",network.PredictedRaw_dBm,network.MeasuredMedian_dBm); ...
        metric_row(radius,"network_best_calibrated",network.PredictedCalibrated_dBm,network.MeasuredMedian_dBm)]; %#ok<AGROW>
end
summary=struct('CampaignID',C.CampaignID,'Mode',C.Mode,'Model',modelLabel, ...
    'Trials',height(F),'ReceivedTrials',nnz(F.TTS_received), ...
    'NotFoundTrials',nnz(~F.TTS_received),'GatewayReceptionRows',height(R), ...
    'StoredReception_pct',100*nnz(F.TTS_received)/height(F), ...
    'StreetCandidatesWithRSSI',height(primaryNetwork), ...
    'CandidateGatewayPairs',height(primaryLinks), ...
    'TimePositionSemanticsVerified',C.TimePositionSemanticsVerified, ...
    'GNSSAccuracyVerified',C.GNSSAccuracyVerified, ...
    'MedianFTMinusRadio_s',median(R.FTMinusRadio_s,'omitnan'), ...
    'FrequencyRange_MHz',[min(R.Frequency_Hz) max(R.Frequency_Hz)]/1e6, ...
    'Threshold_dBm',threshold, ...
    'Scope',"Concordancia provisional de corredor; no certifica precision instrumental ni optimalidad");
if ~isfolder(C.OutputRoot),mkdir(C.OutputRoot);end
folder=tempname(C.OutputRoot);
mkdir(folder);
writetable(F,fullfile(folder,'ensayos_asociados.csv'));
writetable(R,fullfile(folder,'recepciones_con_predicciones.csv'));
writetable(primaryLinks,fullfile(folder,'intersecciones_por_gateway.csv'));
writetable(primaryNetwork,fullfile(folder,'intersecciones_mejor_enlace.csv'));
writetable(allMetrics,fullfile(folder,'metricas_por_radio.csv'));
write_json(fullfile(folder,'resumen.json'),summary);
write_json(fullfile(folder,'configuracion_usada.json'),C);
copyfile(fullfile(C.InputRoot,'manifest_entradas.json'),folder);
copyfile(fullfile(C.InputRoot,'trazabilidad_fuentes.json'),folder);
copyfile(mfilename('fullpath')+".m",fullfile(folder,'motor_ejecutado.m'));
for helper=["RF_uplink_trazable","trazable_sha256","run_benchmark"]
    copyfile(which(helper),fullfile(folder,helper+".m"));
end
if strlength(C.CalibrationFile)>0,copyfile(C.CalibrationFile,fullfile(folder,'calibracion_aplicada.json'));end
if C.Mode=="physical_model"
    writetable(ground,fullfile(folder,'elevaciones_asociadas.csv'));
    save(fullfile(folder,'modelo_RF_scenario.mat'),'matrix','bin','points','C','-v7.3');
    if C.RunBenchmark
        run_benchmark(T,matrix,bin,points,C,folder);
    end
end
if C.MakeFigures && ~isempty(primaryNetwork)
    fig=figure('Visible','off','Color','w');cleanup=onCleanup(@()close(fig));
    scatter(primaryNetwork.PredictedRaw_dBm,primaryNetwork.MeasuredMedian_dBm,24,'filled');
    hold on; lims=[min([xlim ylim]) max([xlim ylim])];plot(lims,lims,'k--');
    xlabel('RSSI predicho original (dBm)');ylabel('RSSI uplink mediano observado (dBm)');
    title('Contraste provisional por interseccion: sin ajuste al recorrido');grid on;
    exportgraphics(fig,fullfile(folder,'contraste_original.png'),'Resolution',200);
end
out=struct('Folder',string(folder),'Summary',summary,'Metrics',allMetrics, ...
    'Links',primaryLinks,'Network',primaryNetwork);
write_output_hashes(folder);
disp(summary);fprintf('Resultados preservados en: %s\n',folder);
end

function [x,y]=local_xy(lat,lon,o)
x=deg2rad(lon-o(2))*6371000*cosd(o(1));y=deg2rad(lat-o(1))*6371000;
end

function A=aggregate_links(R,campaign,version,fingerprint)
A=table();
keys=string(R.Node_ID)+"|"+R.Gateway_ID;[u,~,g]=unique(keys);
for k=1:numel(u)
    s=R(g==k,:);
    row=table(s.Node_ID(1),s.Gateway_ID(1),s.Primary_Street(1),s.Intersecting_Street(1), ...
        height(s),median(s.RSSI_dBm,'omitnan'),median(s.PredictedRaw_dBm,'omitnan'), ...
        median(s.PredictedCalibrated_dBm,'omitnan'),median(s.MatchDistance_m), ...
        campaign,version,fingerprint,strjoin(s.FrameKey,';'), ...
        'VariableNames',{'Node_ID','Gateway_ID','Primary_Street','Intersecting_Street', ...
        'N_receptions','MeasuredMedian_dBm','PredictedRaw_dBm','PredictedCalibrated_dBm', ...
        'MatchMedian_m','Campaign_ID','Model_Version','BaseModelSHA256','FrameKeys'});
    A=[A;row]; %#ok<AGROW>
end
end

function A=aggregate_network(F,T)
A=table();ids=unique(F.Node_ID(isfinite(F.BestReceived_dBm)));
for k=1:numel(ids)
    s=F(F.Node_ID==ids(k),:);[~,j]=ismember(ids(k),T.Node_ID);
    row=table(ids(k),T.Primary_Street(j),T.Intersecting_Street(j),height(s),nnz(s.TTS_received), ...
        median(s.BestReceived_dBm,'omitnan'),median(s.BestPredictedRaw_dBm,'omitnan'), ...
        median(s.BestPredictedCalibrated_dBm,'omitnan'),isfinite(T.Measured_Field_RSSI_dBm(j)), ...
        'VariableNames',{'Node_ID','Primary_Street','Intersecting_Street','N_tests','N_received', ...
        'MeasuredMedian_dBm','PredictedRaw_dBm','PredictedCalibrated_dBm','HistoricalRSSIAvailable'});
    A=[A;row]; %#ok<AGROW>
end
end

function out=metric_row(radius,label,x,y)
v=isfinite(x)&isfinite(y);x=x(v);y=y(v);e=y-x;n=numel(e);
rmse=NaN;mae=NaN;bias=NaN;r2=NaN;p6=NaN;p10=NaN;
if n>0
    rmse=sqrt(mean(e.^2));mae=mean(abs(e));bias=mean(e);
    sst=sum((y-mean(y)).^2);if sst>0,r2=1-sum(e.^2)/sst;end
    p6=100*mean(abs(e)<=6);p10=100*mean(abs(e)<=10);
end
out=table(radius,label,n,rmse,mae,bias,r2,p6,p10,'VariableNames', ...
    {'Radius_m','Series','N','RMSE_dB','MAE_dB','Bias_obs_minus_pred_dB','Predictive_R2','Within6_pct','Within10_pct'});
end

function verify_inputs(root)
M=jsondecode(fileread(fullfile(root,'manifest_entradas.json')));
for k=1:numel(M.Files)
    actual=sha256_file(fullfile(root,M.Files(k).Name));
    assert(actual==string(M.Files(k).SHA256),'Trazable:Hash', ...
        'Entrada modificada: %s. Regenerar y documentar la procedencia.',M.Files(k).Name);
end
sources=jsondecode(fileread(fullfile(root,'trazabilidad_fuentes.json')));
for k=1:numel(sources.Files)
    path=fullfile(root,'..','fuentes',sources.Files(k).Name);
    assert(sha256_file(path)==string(sources.Files(k).SHA256), ...
        'Trazable:SourceHash','El archivo fuente cambio: %s',sources.Files(k).Name);
end
end

function value=sha256_file(path)
value=trazable_sha256(path,"file");
end

function value=sha256_text(text)
value=trazable_sha256(text,"text");
end

function write_json(path,data)
fid=fopen(path,'w','n','UTF-8');assert(fid>=0,'Trazable:Write','No se pudo escribir %s',path);
c=onCleanup(@()fclose(fid));fprintf(fid,'%s',jsonencode(data,'PrettyPrint',true));
end

function write_output_hashes(folder)
files=dir(folder);entries=struct('Name',{},'SHA256',{});
for k=1:numel(files)
    if files(k).isdir,continue;end
    entries(end+1)=struct('Name',files(k).name,'SHA256',sha256_file(fullfile(folder,files(k).name))); %#ok<AGROW>
end
write_json(fullfile(folder,'manifest_resultados.json'),struct('Files',entries));
end
