function Ingesta_Dual_TTN_FieldTester
    % =====================================================================
    % TESIS DOCTORAL: INGESTA DUAL EMPÍRICA (FIELD TESTER + TTN STORAGE API)
    % Comparación con Gemelo Digital 3D (PUCESA & PALTAS, ROI +20%)
    % Métricas de Validación Rigurosa para Publicaciones MDPI
    % =====================================================================
    clc; close all; warning('off', 'all');
    
    disp('=================================================================');
    disp(' INGESTADOR EMPÍRICO DUAL: ARCHIVOS LOCALES + THE THINGS STACK   ');
    disp('=================================================================');
    
    %% 1. CONFIGURACIÓN DE RUTAS Y SERVIDOR TTN
    dir_fieldtest = 'D:\DOCTORADOUPS\TESIS\OCTUBRE\FieldTester\22octubre';
    
    % Búsqueda dinámica de la carpeta de resultados del Gemelo ROI +20%
    base_results = 'D:\DOCTORADOUPS\TESIS\OCTUBRE';
    roi_folders = dir(fullfile(base_results, 'Results_DualGW_ROI20_*'));
    if isempty(roi_folders)
        % Alternativa: usar carpeta general previa de 2 GWs
        roi_folders = dir(fullfile(base_results, 'Results_Ambato_2GWs_*'));
    end
    
    if isempty(roi_folders)
        error('No se localizó la carpeta de resultados del Gemelo Digital en: %s', base_results);
    end
    dir_twin = fullfile(base_results, roi_folders(end).name);
    fprintf(' -> Carpeta del Gemelo Digital detectada: %s\n', roi_folders(end).name);
    
    twin_csv = fullfile(dir_twin, 'Empirical_ROI20_Dual_Installed_Gateways.csv');
    if ~isfile(twin_csv)
        % Búsqueda de cualquier CSV empírico disponible en la subcarpeta
        alt_csv = dir(fullfile(dir_twin, 'Empirical_*.csv'));
        if isempty(alt_csv)
            error('No se encontró el CSV del Gemelo Digital dentro de: %s', dir_twin);
        end
        twin_csv = fullfile(dir_twin, alt_csv(1).name);
    end
    fprintf(' -> Archivo del Gemelo cargado: %s\n', twin_csv);
    
    dir_out = fullfile(dir_twin, 'Validacion_Empirica_Consolidada');
    if ~exist(dir_out, 'dir'), mkdir(dir_out); end
    
    % Configuración de la API REST de The Things Stack (Captura de pantalla)
    TTN_Config.Host     = 'coberturaiotambato.nam1.cloud.thethings.industries';
    TTN_Config.AppID    = 'field-tester-ambato';
    TTN_Config.DeviceID = 'fieldtester';
    % Introduce la cadena secreta completa NNSXS... generada en tu consola:
    TTN_Config.APIKey   = getenv('TTS_API_KEY'); 
    TTN_Config.DownloadOnline = false; % Cambiar a true si deseas consultar el servidor vía REST
    
    %% 2. INGESTA A: ARCHIVOS LOCALES DEL DRIVE TEST (.CSV)
    disp(' -> [FASE 1] Procesando registros locales del Field Tester...');
    T_Local = Ingest_Local_FieldTester_CSVs(dir_fieldtest);
    fprintf('    - Registros locales válidos con GPS: %d\n', height(T_Local));
    
    %% 3. INGESTA B: DESCARGA REMOTA VÍA REST (TTN STORAGE INTEGRATION)
    T_Online = table();
    if TTN_Config.DownloadOnline && ~contains(TTN_Config.APIKey, 'PONER_AQUI')
        disp(' -> [FASE 2] Consultando paquetes en The Things Stack Storage API...');
        T_Online = Ingest_TTN_Storage_API(TTN_Config);
        fprintf('    - Registros remotos obtenidos desde TTN: %d\n', height(T_Online));
    else
        disp(' -> [FASE 2] Consulta online omitida (usando base de datos local consolidada).');
    end
    
    % Fusión y deduplicación espaciotemporal (filtro de paquetes duplicados)
    T_Empirical = Consolidate_Measurements(T_Local, T_Online);
    N_emp = height(T_Empirical);
    fprintf(' -> Total de puntos empíricos únicos consolidados: %d\n\n', N_emp);
    
    if N_emp == 0
        error('No hay datos empíricos válidos para realizar la validación.');
    end
    
    %% 4. CRUCE ESPACIAL CON EL GEMELO DIGITAL 3D (EMPAREJAMIENTO GEODÉSICO)
    disp(' -> [FASE 3] Emparejando mediciones con nodos del Gemelo Digital 3D...');
    T_Twin = readtable(twin_csv);
    
    lat0 = mean(T_Twin.Latitude);
    lon0 = mean(T_Twin.Longitude);
    R_earth = 6371000;
    
    % Proyección métrica euclidiana planar
    Twin_X = deg2rad(T_Twin.Longitude - lon0) * R_earth * cosd(lat0);
    Twin_Y = deg2rad(T_Twin.Latitude - lat0) * R_earth;
    
    Emp_X = deg2rad(T_Empirical.Lon - lon0) * R_earth * cosd(lat0);
    Emp_Y = deg2rad(T_Empirical.Lat - lat0) * R_earth;
    
    Matched_Twin_ID = zeros(N_emp, 1);
    Dist_Offset_m   = zeros(N_emp, 1);
    
    for i = 1:N_emp
        d2 = (Twin_X - Emp_X(i)).^2 + (Twin_Y - Emp_Y(i)).^2;
        [min_d2, best_idx] = min(d2);
        Matched_Twin_ID(i) = best_idx;
        Dist_Offset_m(i)   = sqrt(min_d2);
    end
    
    % Radio de correlación espacial máximo tolerado (40 metros a eje de vía)
    valid_spatial = Dist_Offset_m <= 40;
    fprintf('    - Puntos dentro del corredor vial del modelo (<= 40m): %d (%.1f%%)\n', ...
            sum(valid_spatial), (sum(valid_spatial)/N_emp)*100);
        
    V = T_Empirical(valid_spatial, :);
    V.Twin_Node_ID      = Matched_Twin_ID(valid_spatial);
    V.Spatial_Offset_m  = Dist_Offset_m(valid_spatial);
    V.Simulated_RSSI    = T_Twin.RSSI_Predicted_dBm(V.Twin_Node_ID);
    V.Twin_Serving_GW   = T_Twin.Serving_GW_ID(V.Twin_Node_ID);
    V.Clutter_Profile   = T_Twin.Clutter_Profile(V.Twin_Node_ID);
    V.Elevation_MSNM    = T_Twin.Elevation_MSNM(V.Twin_Node_ID);
    
    % Filtrar enlaces activos en ambos dominios
    valid_rf = (V.Measured_RSSI > -145) & (V.Simulated_RSSI > -145);
    V_Final = V(valid_rf, :);
    
    %% 5. ANÁLISIS ESTADÍSTICO DE AJUSTE (MÉTRICAS DOCTORALES)
    disp(' -> [FASE 4] Computando KPIs metrológicos de propagación...');
    residuos = V_Final.Measured_RSSI - V_Final.Simulated_RSSI;
    bias     = mean(residuos);
    mae      = mean(abs(residuos));
    rmse     = sqrt(mean(residuos.^2));
    sigma_sh = std(residuos);
    
    R_mat = corrcoef(V_Final.Simulated_RSSI, V_Final.Measured_RSSI);
    if numel(R_mat) >= 4, pearson_r = R_mat(1,2); else, pearson_r = 0; end
    
    fprintf('\n ================= REPORTE METROLÓGICO: CAMPO VS GEMELO 3D =================\n');
    fprintf('    * Muestras Empíricas Emparejadas:  %d puntos\n', height(V_Final));
    fprintf('    * Error Medio (Bias / Desvío):     %+.2f dB\n', bias);
    fprintf('    * Error Absoluto Medio (MAE):       %.2f dB\n', mae);
    fprintf('    * Raíz del Error Cuadrático (RMSE): %.2f dB\n', rmse);
    fprintf('    * Desviación de Shadowing (sigma):  %.2f dB\n', sigma_sh);
    fprintf('    * Coeficiente de Correlación (rho): %.3f\n', pearson_r);
    fprintf(' ===========================================================================\n\n');
    
    %% 6. DESAGREGACIÓN DE RECEPCIÓN POR ESTACIÓN BASE
    gw1_count = sum(V_Final.Measured_GW_ID == 1);
    gw2_count = sum(V_Final.Measured_GW_ID == 2);
    fprintf(' Tramas recibidas clasificadas por Gateway:\n');
    fprintf('    - Gateway2PUCESA (ID 1, Cota 2855 m): %d paquetes capturados\n', gw1_count);
    fprintf('    - Gateway1PALTAS (ID 2, Cota 2696 m): %d paquetes capturados\n\n', gw2_count);
    
    %% 7. EXPORTACIÓN DE ENTREGABLES CIENTÍFICOS
    out_csv = fullfile(dir_out, 'Validacion_Empirica_PUCESA_PALTAS.csv');
    writetable(V_Final, out_csv);
    fprintf(' -> CSV de validación doctoral exportado en:\n    %s\n', out_csv);
    
    % Generación de Figuras de Calidad MDPI (600 DPI)
    Generate_Scientific_Plots(V_Final, residuos, bias, rmse, sigma_sh, pearson_r, dir_out);
    
    disp('=================================================================');
    disp(' VALIDACIÓN FINALIZADA CON ÉXITO');
    disp('=================================================================');
end

%% ========================================================================
%% INGESTA LOCAL ULTRA-ROBUSTA CON AUTO-CALIBRACIÓN GEODÉSICA
%% ========================================================================
function T_all = Ingest_Local_FieldTester_CSVs(folder)
    T_all = table();
    files = dir(fullfile(folder, '*.csv'));
    
    if isempty(files)
        warning('No se encontraron archivos .csv en el directorio: %s', folder);
        return;
    end
    
    for f = 1:length(files)
        filepath = fullfile(folder, files(f).name);
        fprintf('\n    [+] Analizando archivo: %s\n', files(f).name);
        
        opts = detectImportOptions(filepath);
        opts.VariableNamingRule = 'preserve';
        raw = readtable(filepath, opts);
        
        var_names_raw = string(raw.Properties.VariableNames);
        var_names_low = lower(strrep(strrep(var_names_raw, '.', '_'), ' ', '_'));
        N = height(raw);
        
        % 1. Detección flexible de índices
        lat_col = find(contains(var_names_low, ["lat", "latitude", "gps_lat", "y_coord", "latitud"]), 1);
        lon_col = find(contains(var_names_low, ["lon", "lng", "longitude", "gps_lon", "x_coord", "longitud"]), 1);
        rssi_col = find(contains(var_names_low, ["rssi", "rx_rssi", "measured_rssi", "potencia", "rssi_(dbm)"]), 1);
        snr_col  = find(contains(var_names_low, ["snr", "rx_snr", "measured_snr", "snr_(db)"]), 1);
        gw_col   = find(contains(var_names_low, ["gateway", "gtw", "gw_id", "eui", "serving_gw", "gateway_id"]), 1);
        time_col = find(contains(var_names_low, ["time", "timestamp", "fecha", "date", "received_at"]), 1);
        
        % 2. Extracción numérica con saneamiento de caracteres
        Lat  = Robust_Numeric_Cast(raw, lat_col, N);
        Lon  = Robust_Numeric_Cast(raw, lon_col, N);
        RSSI = Robust_Numeric_Cast(raw, rssi_col, N);
        SNR  = Robust_Numeric_Cast(raw, snr_col, N);
        
        % Depuración en consola para inspección metrológica
        fprintf('        * Filas leídas: %d\n', N);
        if N > 0 && ~isempty(lat_col) && ~isempty(lon_col)
            sample_lat = Lat(find(~isnan(Lat), 2, 'first'));
            sample_lon = Lon(find(~isnan(Lon), 2, 'first'));
            if ~isempty(sample_lat) && ~isempty(sample_lon)
                fprintf('        * Muestra cruda extraída -> Lat: %f | Lon: %f\n', sample_lat(1), sample_lon(1));
            else
                fprintf('        [!] ADVERTENCIA: La columna fue detectada pero todos los valores resultaron NaN.\n');
            end
        end
        
        % 3. Corrección de Escalas Geodésicas Heterogéneas
        valid_raw = ~isnan(Lat) & ~isnan(Lon) & (Lat ~= 0);
        if any(valid_raw)
            med_lat = median(abs(Lat(valid_raw)));
            med_lon = median(abs(Lon(valid_raw)));
            
            % Caso A: Microgrados enteros (escala 1e7 o 1e6)
            if med_lat > 1e6
                Lat = Lat / 1e7; Lon = Lon / 1e7;
                disp('        [!] Coordenadas normalizadas desde escala 1e-7.');
            elseif med_lat > 1e4
                Lat = Lat / 1e6; Lon = Lon / 1e6;
                disp('        [!] Coordenadas normalizadas desde escala 1e-6.');
            % Caso B: Formato Grados y Minutos (DDMM.MMMM)
            elseif med_lat > 10 && med_lat < 90
                % Latitud Ambato ~ 01° 15' S -> 115.XXXX
                deg_lat = fix(Lat / 100);
                min_lat = Lat - (deg_lat * 100);
                Lat = deg_lat + (min_lat / 60);
                
                deg_lon = fix(Lon / 100);
                min_lon = Lon - (deg_lon * 100);
                Lon = deg_lon + (min_lon / 60);
                disp('        [!] Coordenadas convertidas desde formato NMEA (DDMM.MMMM).');
            end
            
            % Garantizar cuadrante Hemisferio Sur y Occidental para Ambato
            if median(Lat(valid_raw)) > 0 && median(Lat(valid_raw)) < 5
                Lat = -abs(Lat); % Asegurar latitud negativa (Ecuador central)
            end
            if median(Lon(valid_raw)) > 0 && median(Lon(valid_raw)) < 90
                Lon = -abs(Lon); % Asegurar longitud negativa (Oeste de Greenwich)
            end
        end
        
        % 4. Tratamiento del Gateway Servidor
        if ~isempty(gw_col)
            GW_Str = string(raw{:, gw_col});
        else
            GW_Str = repmat("gateway-unknown", N, 1);
        end
        
        if ~isempty(time_col)
            Time_Str = string(raw{:, time_col});
        else
            Time_Str = repmat(string(datestr(now, 'yyyy-mm-ddTHH:MM:SSZ')), N, 1);
        end
        
        % Mapeo de identificadores físicos instalados:
        % GW 1 = PUCESA (gateway2), GW 2 = PALTAS (gateway1)
        GW_ID = zeros(N, 1);
        GW_ID(contains(lower(GW_Str), ["pucesa", "gateway2", "gw2"])) = 1;
        GW_ID(contains(lower(GW_Str), ["paltas", "gateway1", "gw1"])) = 2;
        
        if all(GW_ID == 0) && ~isempty(gw_col)
            num_gw = Robust_Numeric_Cast(raw, gw_col, N);
            valid_num = ismember(num_gw, [1, 2]);
            GW_ID(valid_num) = num_gw(valid_num);
        end
        
        % Por defecto, si no hay columna de gateway, se asume recepción dual/activa
        if all(GW_ID == 0)
            GW_ID(:) = 1; % Asignación preliminar para procesar métricas
        end
        
        % 5. Filtro Geodésico Amplio (Tungurahua / Región Sierra Centro)
        valid = ~isnan(Lat) & ~isnan(Lon) & (Lat ~= 0) & ...
                (Lat >= -2.0 & Lat <= -0.5) & ...
                (Lon >= -79.5 & Lon <= -78.0);
            
        fprintf('        * Filas con coordenadas geográficas validadas: %d\n', sum(valid));
        
        if sum(valid) > 0
            sub_tbl = table(Lat(valid), Lon(valid), RSSI(valid), SNR(valid), ...
                            GW_Str(valid), GW_ID(valid), Time_Str(valid), ...
                            'VariableNames', {'Lat', 'Lon', 'Measured_RSSI', 'Measured_SNR', ...
                                              'Gateway_Name', 'Measured_GW_ID', 'Timestamp'});
            T_all = [T_all; sub_tbl]; %#ok<AGROW>
        end
    end
end

%% ========================================================================
%% INGESTA ONLINE: STORAGE INTEGRATION REST API DE THE THINGS STACK
%% ========================================================================
function T_online = Ingest_TTN_Storage_API(cfg)
    T_online = table();
    url = sprintf('https://%s/api/v3/as/applications/%s/packages/storage/uplink_message?limit=1000&order=-received_at', ...
                  cfg.Host, cfg.AppID);
              
    options = weboptions('HeaderFields', {'Authorization', ['Bearer ', cfg.APIKey]; ...
                                          'Accept', 'application/json'}, ...
                         'Timeout', 30);
    try
        raw_resp = webread(url, options);
    catch ME
        warning('Fallo en la comunicación REST con The Things Stack: %s', ME.message);
        return;
    end
    
    % Procesar respuestas en bloques JSON / NDJSON
    if ischar(raw_resp) || isstring(raw_resp)
        lines = splitlines(strtrim(string(raw_resp)));
        entries = cell(length(lines), 1);
        for k = 1:length(lines)
            if ~isempty(lines{k}), entries{k} = jsondecode(lines{k}); end
        end
        entries(cellfun(@isempty, entries)) = [];
    elseif iscell(raw_resp)
        entries = raw_resp;
    elseif isstruct(raw_resp)
        entries = num2cell(raw_resp);
    else
        entries = {};
    end
    
    N = length(entries);
    Lat = nan(N, 1); Lon = nan(N, 1); RSSI = nan(N, 1); SNR = nan(N, 1); 
    GW_Str = strings(N, 1); Time_Str = strings(N, 1);
    
    for i = 1:N
        item = entries{i};
        if isfield(item, 'result') && isstruct(item.result), item = item.result; end
        
        if isfield(item, 'uplink_message')
            um = item.uplink_message;
            if isfield(um, 'decoded_payload')
                dp = um.decoded_payload;
                if isfield(dp, 'latitude'),  Lat(i) = dp.latitude; end
                if isfield(dp, 'longitude'), Lon(i) = dp.longitude; end
            end
            if isfield(um, 'rx_metadata') && ~isempty(um.rx_metadata)
                rx = um.rx_metadata(1);
                if iscell(rx), rx = rx{1}; end
                if isfield(rx, 'rssi'), RSSI(i) = rx.rssi; end
                if isfield(rx, 'snr'),  SNR(i)  = rx.snr;  end
                if isfield(rx, 'gateway_ids') && isfield(rx.gateway_ids, 'gateway_id')
                    GW_Str(i) = string(rx.gateway_ids.gateway_id);
                end
            end
            if isfield(um, 'received_at')
                Time_Str(i) = string(um.received_at);
            end
        end
    end
    
    GW_ID = zeros(N, 1);
    GW_ID(contains(lower(GW_Str), ["pucesa", "gateway2", "gw2"])) = 1;
    GW_ID(contains(lower(GW_Str), ["paltas", "gateway1", "gw1"])) = 2;
    
    valid = ~isnan(Lat) & ~isnan(Lon) & (Lat ~= 0);
    T_online = table(Lat(valid), Lon(valid), RSSI(valid), SNR(valid), ...
                     GW_Str(valid), GW_ID(valid), Time_Str(valid), ...
                     'VariableNames', {'Lat', 'Lon', 'Measured_RSSI', 'Measured_SNR', ...
                                       'Gateway_Name', 'Measured_GW_ID', 'Timestamp'});
end

%% ========================================================================
%% CONSOLIDACIÓN Y DEDUPLICACIÓN
%% ========================================================================
function T_merged = Consolidate_Measurements(T1, T2)
    T_merged = [T1; T2];
    if isempty(T_merged), return; end
    
    % Llave de resolución métrica: Coordenadas redondeadas a 5 decimales (~1.1 m)
    coords = round([T_merged.Lat, T_merged.Lon], 5);
    [~, unique_idx] = unique([coords, double(T_merged.Measured_GW_ID)], 'rows');
    T_merged = T_merged(unique_idx, :);
end

%% ========================================================================
%% FUNCIONES AUXILIARES: CASTING NUMÉRICO Y GRAFICACIÓN CIENTÍFICA
%% ========================================================================
function vec = Cast_To_Double(tbl, col_idx, N)
    if isempty(col_idx), vec = nan(N, 1); return; end
    c = tbl{:, col_idx};
    if isnumeric(c), vec = double(c);
    elseif iscell(c) || isstring(c) || ischar(c) || iscategorical(c)
        s = strrep(string(c), ',', '.');
        vec = str2double(s);
    else, vec = nan(N, 1); end
    vec = vec(:);
end

%% ========================================================================
%% GENERACIÓN DE GRÁFICAS CIENTÍFICAS NATIVAS (MATLAB BASE - SIN TOOLBOXES)
%% ========================================================================
function Generate_Scientific_Plots(V, res, bias, rmse, sigma, rho, out_dir)
% 1. Diagrama de Dispersión y Regresión Lineal
f1 = figure('Name', 'Ajuste RF Modelo 3D vs Medido', 'Color', 'w', 'Position', [100 100 700 520]);
a1 = axes(f1);

scatter(a1, V.Simulated_RSSI, V.Measured_RSSI, 36, V.Elevation_MSNM, 'filled', ...
    'MarkerFaceAlpha', 0.7, 'MarkerEdgeColor', [0.2 0.2 0.2]);
hold(a1, 'on'); grid(a1, 'on');
cb = colorbar(a1); 
ylabel(cb, 'Cota Topográfica (msnm)', 'FontSize', 10);
colormap(a1, 'jet');

% Ajuste polinomial de primer grado (Regresión lineal)
p = polyfit(V.Simulated_RSSI, V.Measured_RSSI, 1);
x_min = min(V.Simulated_RSSI) - 2;
x_max = max(V.Simulated_RSSI) + 2;
x_ax = linspace(x_min, x_max, 100);

plot(a1, x_ax, polyval(p, x_ax), 'r-', 'LineWidth', 2.2);

% Línea de identidad ideal 1:1
y_lims = [min([V.Simulated_RSSI; V.Measured_RSSI]) - 5, max([V.Simulated_RSSI; V.Measured_RSSI]) + 5];
plot(a1, y_lims, y_lims, 'k--', 'LineWidth', 1.2);

xlabel(a1, 'Predicted RSSI (dBm) - 3D ITU-R Meso-Cellular Model', 'FontSize', 10.5, 'FontWeight', 'bold');
ylabel(a1, 'Measured RSSI (dBm) - Field Tester Drive-Test', 'FontSize', 10.5, 'FontWeight', 'bold');
title(a1, sprintf('Empirical Cross-Validation (RMSE = %.2f dB, \\rho = %.3f, Bias = %+.2f dB)', ...
    rmse, rho, bias), 'FontSize', 11, 'FontWeight', 'bold');

legend(a1, 'Empirical Samples (Ambato Drive-Test)', ...
    sprintf('Linear Fit (y = %.2fx %+.1f)', p(1), p(2)), ...
    'Ideal 1:1 Tracking', 'Location', 'northwest');

drawnow;
exportgraphics(f1, fullfile(out_dir, 'Fig_Correlation_RSSI_600DPI.png'), 'Resolution', 600);
savefig(f1, fullfile(out_dir, 'Fig_Correlation_RSSI.fig'));

% 2. Histograma de Residuos y Ajuste Normal (Sin normpdf de Toolbox)
f2 = figure('Name', 'Distribución de Residuos de Propagación', 'Color', 'w', 'Position', [820 100 660 500]);
a2 = axes(f2);

h = histogram(a2, res, 15, 'Normalization', 'pdf', 'FaceColor', [0.2 0.5 0.7], ...
    'EdgeColor', 'k', 'FaceAlpha', 0.7);
hold(a2, 'on'); grid(a2, 'on');

% Formulación gaussiana nativa en MATLAB Base
xr = linspace(min(res) - 5, max(res) + 5, 250);
if sigma > 0
    pdf_gauss = (1 / (sigma * sqrt(2 * pi))) .* exp(-0.5 * ((xr - bias) ./ sigma).^2);
    plot(a2, xr, pdf_gauss, 'r-', 'LineWidth', 2.2);
end

xlabel(a2, 'Residual Error: RSSI_{measured} - RSSI_{simulated} (dB)', 'FontSize', 10.5, 'FontWeight', 'bold');
ylabel(a2, 'Probability Density', 'FontSize', 10.5, 'FontWeight', 'bold');
title(a2, 'Empirical Shadowing Distribution (Log-Normal Fit)', 'FontSize', 11, 'FontWeight', 'bold');

legend(a2, 'Measured Residuals', ...
    sprintf('Gaussian Shadowing Fit (\\mu = %.2f dB, \\sigma = %.2f dB)', bias, sigma), ...
    'Location', 'northeast');

drawnow;
exportgraphics(f2, fullfile(out_dir, 'Fig_Residual_Shadowing_600DPI.png'), 'Resolution', 600);
savefig(f2, fullfile(out_dir, 'Fig_Residual_Shadowing.fig'));
end
%% ========================================================================
%% CASTING VECTORIAL ROBUSTO (LIMPIEZA REGEX Y MANEJO DE SEPARADORES)
%% ========================================================================
function vec = Robust_Numeric_Cast(tbl, col_idx, N)
if isempty(col_idx)
    vec = nan(N, 1);
    return;
end

col_data = tbl{:, col_idx};

if isnumeric(col_data)
    vec = double(col_data);
else
    % Convertir a string uniforme
    str_data = string(col_data);
    % Limpieza de espacios en blanco, comillas dobles y simples
    str_data = strtrim(str_data);
    str_data = regexprep(str_data, '["'']', '');
    % Normalizar coma decimal a punto
    str_data = strrep(str_data, ',', '.');
    % Filtrar cualquier carácter que no sea numérico, signo o punto
    str_data = regexprep(str_data, '[^0-9\.\+\-eE]', '');

    vec = str2double(str_data);
end
vec = vec(:);
end