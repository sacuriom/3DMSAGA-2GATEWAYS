function verificar_revision()
% Ejecutar desde esta carpeta o con addpath. No mide exactitud fisica.
root=fileparts(mfilename('fullpath'));addpath(root);
files={'MDPI_3DMSAGA_Trazable','RF_uplink_trazable','config_campana_ambato', ...
    'run_benchmark','ajustar_offset_independiente'};
for k=1:numel(files)
    messages=checkcode(which(files{k}),'-id');
    fprintf('%s: %d mensajes de analizador\n',files{k},numel(messages));
    for j=1:numel(messages)
        fprintf('  linea %d: %s\n',messages(j).line(1),messages(j).message);
    end
end
C=config_campana_ambato();C.MakeFigures=false;
out=MDPI_3DMSAGA_Trazable(C);
assert(out.Summary.Trials==291 && out.Summary.ReceivedTrials==267);
assert(out.Summary.GatewayReceptionRows==397);
assert(out.Summary.StreetCandidatesWithRSSI==103);
assert(out.Summary.CandidateGatewayPairs==150);
m=out.Metrics(out.Metrics.Radius_m==45 & out.Metrics.Series=="network_best_calibrated",:);
assert(m.N==103 && abs(m.RMSE_dB-11.764699543116508)<1e-8);
assert(abs(m.Within6_pct-39.80582524271845)<1e-8);
C.Mode="physical_model";
try
    MDPI_3DMSAGA_Trazable(C);
    error('Trazable:Test','Se acepto un modelo con condiciones desconocidas.');
catch ME
    assert(strcmp(ME.identifier,'Trazable:Parameters'));
end
save(fullfile(root,'prueba_MATLAB_real.mat'),'out');
test_presupuesto_uplink(root);
test_calibracion_independiente(root);
fprintf('Pruebas MATLAB de reproduccion y rechazo de condiciones incompletas: OK\n');
end

function test_presupuesto_uplink(root)
% Valores sinteticos SOLO para verificar ecuaciones; no son datos de campo.
C=config_campana_ambato();C.Mode="physical_model";C.RunBenchmark=false;
C.Model.ParametersDocumented=true;C.Model.TxPower_dBm=30;
C.Model.PowerSettingInterpretationVerified=true;
C.Model.TxGain_dBi=2;C.Model.TxCableLoss_dB=1;C.Model.TxHeightAGL_m=2;
C.Model.TxHardwareSource="synthetic_test_only";
C.Model.VerticalDatum="SYNTHETIC_TEST_ONLY";
C.Model.Sensitivity_dBm=-131;C.Model.SensitivitySource="synthetic_test_only";
C.Model.PathExponents=[2 2 2];C.Model.ClutterLoss_dB=[0 0 0];C.Model.ReferenceFrequencyMHz=904.5;
for k=1:2
    C.Gateways(k).RxGain_dBi=5;C.Gateways(k).RxCableLoss_dB=1;
    C.Gateways(k).RxHeightAGL_m=2;C.Gateways(k).HardwareSource="synthetic_test_only";
    C.Gateways(k).CoordinatesConfirmed=true;
end
folder=fullfile(root,'tests_tmp','presupuesto_sintetico');if ~isfolder(folder),mkdir(folder);end
lat=-1.25;lon=-78.63;delta=rad2deg(100/(6371000*cosd(lat)));
T=table([1;2],[lat;lat],[lon;lon+delta],["Residential";"Residential"], ...
    'VariableNames',{'Node_ID','Latitude','Longitude','Clutter_Class'});
E=table(T.Latitude,T.Longitude,[1000;1000],repmat("SYNTHETIC_TEST_ONLY",2,1), ...
    repmat("synthetic_test_only",2,1),'VariableNames', ...
    {'Latitude','Longitude','GroundElevation_m','VerticalDatum','ElevationSource'});
C.Model.GroundElevationCSV=fullfile(folder,'ground_synthetic.csv');writetable(E,C.Model.GroundElevationCSV);
R=table([904500000;904500000],[30;30],'VariableNames',{'Frequency_Hz','FT_Power_dBm'});
[A,~,~,~,~]=RF_uplink_trazable(T,C,R);
expected=30+2-1+5-1-(20*log10(904.5)-27.55)-20*log10(100);
assert(abs(A(2,1)-expected)<1e-7,'Trazable:BudgetTest','Error de signos/distancia en presupuesto uplink.');
C.Model.TxPower_dBm=33;B=RF_uplink_trazable(T,C,R);
assert(max(abs((B(:)-A(:))-3))<1e-10,'Trazable:PowerTest','La potencia no se propaga correctamente.');
E.Longitude(1)=E.Longitude(1)+0.00001;writetable(E,C.Model.GroundElevationCSV);
try
    RF_uplink_trazable(T,C,R);error('Trazable:Test','Se acepto una elevacion sin correspondencia.');
catch ME
    assert(strcmp(ME.identifier,'Trazable:ElevationMatch'));
end
fprintf('Presupuesto sintetico, respuesta +3 dB y rechazo de cotas sin coordenada: OK\n');
end

function test_calibracion_independiente(root)
% Entrenamiento artificial etiquetado; no se entrega como resultado de campo.
folder=fullfile(root,'tests_tmp','offset_sintetico');if ~isfolder(folder),mkdir(folder);end
N=40;gw=[repmat("gateway1",20,1);repmat("gateway2",20,1)];pred=-100*ones(N,1);
obs=pred+[3*ones(20,1);-2*ones(20,1)];campaign=repmat("SYNTHETIC_TRAINING_ONLY",N,1);
version=repmat("SYNTHETIC_MODEL_ONLY",N,1);finger=repmat(string(repmat('0',1,64)),N,1);
keys="SYNTHETIC_FRAME_"+string((1:N)');
T=table(gw,pred,obs,campaign,version,finger,keys,'VariableNames', ...
    {'Gateway_ID','PredictedRaw_dBm','MeasuredMedian_dBm','Campaign_ID','Model_Version','BaseModelSHA256','FrameKeys'});
path=fullfile(folder,'training_synthetic.csv');writetable(T,path);
coef=ajustar_offset_independiente(path,"SYNTHETIC_TRAINING_ONLY",fullfile(folder,'offset_synthetic.json'));
assert(all([coef.Gateways.Slope]==1));assert(isequal([coef.Gateways.Offset_dB],[3 -2]));
assert(numel(coef.TrainingFrameKeys)==40);
fprintf('Calibracion sintetica: offsets separados, pendiente fija y trazabilidad de tramas: OK\n');
end
