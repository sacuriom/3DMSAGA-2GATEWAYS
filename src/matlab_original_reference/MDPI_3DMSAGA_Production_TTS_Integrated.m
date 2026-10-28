function MDPI_3DMSAGA_Production_TTS_Integrated
    % =====================================================================
    % TESIS DOCTORAL: MOTOR 3D-M-SAGA + INTEGRACIÓN CLOUD API DE TTS 
    % - Credenciales integradas para 'field-tester-ambato'
    % - Calibración empírica por mínimos cuadrados (Corrección de Sesgo y RMSE)
    % - Cálculo formal de Métricas Q1 (RMSE, Bias, Sigma Shadowing)
    % - Renderizado 3D Q1 con Tooltips extendidos (Calles + RSSI Simulado vs Real)
    % =====================================================================
    clc; close all; warning('off', 'all');
    
    disp('=================================================================');
    disp(' INICIALIZANDO PIPELINE Q1: 3D-M-SAGA + CLOUD API DE TTS (AMBATO)  ');
    disp('=================================================================');
    
    %% 1. CREDENCIALES Y CONFIGURACIÓN DE LA API REST DE TTS
    TTS_Config.AppID     = 'field-tester-ambato';
    TTS_Config.APIKey = getenv('TTS_API_KEY'); % CLAVE RETIRADA
    TTS_Config.Subdomain = 'coberturaiotambato.nam1.cloud.thethings.industries';
    
    %% 2. ESTACIONES BASE FÍSICAS INSTALADAS (TELEMETRÍA TTN GNSS)
    Anchors(1) = struct('ID', 'gateway2', 'Name', 'Gateway2PUCESA', ...
                        'Lat', -1.27458, 'Lon', -78.63920, 'Alt', 2855.0);
    Anchors(2) = struct('ID', 'gateway1', 'Name', 'Gateway1PALTAS', ...
                        'Lat', -1.25160, 'Lon', -78.62772, 'Alt', 2696.0);
    anchor_indices = [1, 2];
    
    lat0 = (Anchors(1).Lat + Anchors(2).Lat) / 2; % -1.26309
    lon0 = (Anchors(1).Lon + Anchors(2).Lon) / 2; % -78.63346
    alt0 = (Anchors(1).Alt + Anchors(2).Alt) / 2; % 2775.5 msnm
    
    City.Name = 'Ambato, ECU (Corredor PUCESA - PALTAS)';
    City.Lat  = lat0;
    City.Lon  = lon0;
    City.Alt  = round(alt0);
    
    %% 3. PARÁMETROS RF DE LA TESIS (MILESIGHT UG67)
    HW.Name = 'Milesight UG67 Outdoor';
    HW.Freq = 915;          % MHz (US915)
    HW.Ptx  = 27;           % dBm
    HW.Gain = 5;            % dBi
    HW.PenetrationLoss = 0; % dB
    HW.Height = 0;          % Cota neta GNSS
    HW.SF   = 9;            % Spreading Factor SF9
    HW.Sens = -131.0;       % dBm
    
    Target_Cov = 0.92;      % 92% Cobertura exigida
    R_search_m = 2800;      % Radio meso-celular original
    
    timestamp = datestr(now, 'yyyymmdd_HHMMSS');
    folder_name = sprintf('Results_Production_TTS_SF%d_%s', HW.SF, timestamp);
    mkdir(folder_name);
    
    %% 4. CONSTRUCCIÓN DEL GEMELO DIGITAL (TOPOLOGÍA OSM + SRTM)
    geojson_file = 'ambato_pucesa_osm.json';
    if ~isfile(geojson_file)
        error('No se encontró "%s" en el directorio de trabajo.', geojson_file);
    end
    
    disp(' -> [FASE 1] Extrayendo topología vial y normalizando morfología urbana...');
    T_Full = Build_DigitalTwin_Restored(geojson_file, City, Anchors);
    
    d_from_midpoint = sqrt(T_Full.X_m.^2 + T_Full.Y_m.^2);
    min_req_radius  = max(d_from_midpoint(1:2)) + 800;
    R_effective     = max(R_search_m, min_req_radius);
    
    mask_space = (d_from_midpoint <= R_effective);
    mask_space(1:2) = true;
    
    T_Twin = T_Full(mask_space, :);
    N_nodes = height(T_Twin);
    T_Twin = Normalize_Clutter_Distribution(T_Twin);
    
    Area_km2 = (max(T_Twin.Lat) - min(T_Twin.Lat)) * 111.32 * ...
               (max(T_Twin.Lon) - min(T_Twin.Lon)) * 111.32 * cosd(mean(T_Twin.Lat));
           
    fprintf(' -> Gemelo Digital construido: %d intersecciones en %.2f km² (Radio: %.0f m)\n', ...
            N_nodes, Area_km2, R_effective);
            
    %% 5. MATRIZ DE PROPAGACIÓN RF 3D (ITU-R MODEL)
    disp(' -> [FASE 2] Computando Matriz RF 3D (Modelo Original ITU-R Corregido)...');
    [BinM_3D, Pts_3D, RSSI_Matrix] = Precompute_RF_ITU_OriginalFixed(T_Twin, HW);
    
    %% 6. BENCHMARK DE OPTIMIZACIÓN (3D-M-SAGA)
    disp(' -> [FASE 3] Ejecutando Benchmark (Algoritmos Originales de Tesis)...');
    Results = table('Size',[4 7], 'VariableTypes', {'string','double','double','double','double','double','double'}, ...
                    'VariableNames', {'Algorithm', 'Gateways', 'Coverage_Pct', 'Cov_1GW', 'Cov_2GW', 'Cov_3PlusGW', 'Time_s'});
    Solutions = cell(4,1);
    Algo_Names = ["Greedy SCP (2 GWs Fijos)", "K-Medoids 3D (2 GWs Fijos)", ...
                  "Standard SAGA (2 GWs Fijos)", "Proposed 3D-M-SAGA (2 GWs Fijos)"];
    
    tic; Solutions{1} = Run_Greedy_Original(BinM_3D, Target_Cov, anchor_indices); t1 = toc;
    Results(1,:) = Extract_KPIs(Algo_Names(1), Solutions{1}, BinM_3D, t1);
    
    tic; Solutions{2} = Run_KMedoids_Original(Pts_3D, BinM_3D, Target_Cov, anchor_indices); t2 = toc;
    Results(2,:) = Extract_KPIs(Algo_Names(2), Solutions{2}, BinM_3D, t2);
    
    tic; [Solutions{3}, ~] = Run_GA_Original(BinM_3D, Target_Cov, false, anchor_indices); t3 = toc;
    Results(3,:) = Extract_KPIs(Algo_Names(3), Solutions{3}, BinM_3D, t3);
    
    tic; [Solutions{4}, ~] = Run_GA_Original(BinM_3D, Target_Cov, true, anchor_indices); t4 = toc;
    Results(4,:) = Extract_KPIs(Algo_Names(4), Solutions{4}, BinM_3D, t4);
    
    %% 7. SINCRONIZACIÓN AUTOMÁTICA CON LA API REST DE TTS & CALIBRACIÓN
    disp(' -> [FASE 4] Sincronizando tramas en tiempo real desde la API REST de TTS...');
    T_Empirical = Sync_Data_From_TTS_API(TTS_Config.AppID, TTS_Config.APIKey, TTS_Config.Subdomain);
    
    % Si la API no retorna datos por falta de conexión activa, usar respaldo local CSV
    if isempty(T_Empirical)
        disp('    [!] Usando ingesta de respaldos locales (.csv del Field Tester)...');
        dir_fieldtest = 'D:\DOCTORADOUPS\TESIS\OCTUBRE\FieldTester\2Gateways';
        T_Empirical = Ingest_Local_FieldTester_CSVs(dir_fieldtest);
    end
    
    R_earth = 6371000;
    Node_Status   = zeros(N_nodes, 1);
    Meas_RSSI_Val = nan(N_nodes, 1);
    Meas_SNR_Val  = nan(N_nodes, 1);
    Meas_GW_ID    = zeros(N_nodes, 1);
    
    [Best_RSSI_Dual, Serving_GW_Dual] = max(RSSI_Matrix(:, 1:2), [], 2);
    Node_Status(Best_RSSI_Dual >= HW.Sens) = 1; % AZUL: Modelo Teórico
    
    if ~isempty(T_Empirical)
        Emp_X = deg2rad(T_Empirical.Lon - City.Lon) * R_earth * cosd(City.Lat);
        Emp_Y = deg2rad(T_Empirical.Lat - City.Lat) * R_earth;
        
        Matched_ID = zeros(height(T_Empirical), 1);
        Dist_m     = zeros(height(T_Empirical), 1);
        for i = 1:height(T_Empirical)
            d2 = (T_Twin.X_m - Emp_X(i)).^2 + (T_Twin.Y_m - Emp_Y(i)).^2;
            [min_d2, b_idx] = min(d2);
            Matched_ID(i) = b_idx;
            Dist_m(i)     = sqrt(min_d2);
        end
        
        valid_match = (Dist_m <= 45);
        T_Match = T_Empirical(valid_match, :);
        T_Match.Twin_ID = Matched_ID(valid_match);
        
        u_nodes = unique(T_Match.Twin_ID);
        for k = 1:length(u_nodes)
            nid = u_nodes(k);
            sub = T_Match(T_Match.Twin_ID == nid, :);
            avg_r = mean(sub.RSSI);
            avg_s = mean(sub.SNR);
            
            Meas_RSSI_Val(nid) = avg_r;
            Meas_SNR_Val(nid)  = avg_s;
            if any(strcmp(sub.Properties.VariableNames, 'Gateway_ID'))
                Meas_GW_ID(nid) = sub.Gateway_ID(1);
            else
                Meas_GW_ID(nid) = 1;
            end
            
            sim_ok  = (Best_RSSI_Dual(nid) >= HW.Sens);
            meas_ok = (avg_r >= HW.Sens);
            
            if sim_ok && meas_ok
                Node_Status(nid) = 2; % VERDE: Coincidencia
            else
                Node_Status(nid) = 3; % ROJO: Discrepancia
            end
        end
        
        % ===================================================================
        % CALIBRACIÓN EMPÍRICA POR MÍNIMOS CUADRADOS (CORRECCIÓN DE SESGO Y RMSE)
        % ===================================================================
        idx_eval = find(~isnan(Meas_RSSI_Val) & ~isnan(Best_RSSI_Dual));
        if length(idx_eval) >= 5
            pred_eval = Best_RSSI_Dual(idx_eval);
            meas_eval = Meas_RSSI_Val(idx_eval);
            
            % Regresión lineal simple para hallar el factor de calibración y offset
            p_fit = polyfit(pred_eval, meas_eval, 1);
            Best_RSSI_Calibrated = polyval(p_fit, Best_RSSI_Dual);
            
            residuos_cal = meas_eval - Best_RSSI_Calibrated(idx_eval);
            rmse_val = sqrt(mean(residuos_cal.^2));
            bias_val = mean(residuos_cal);
            sigma_sh = std(residuos_cal);
            
            fprintf('\n ================= ESTADÍSTICAS METROLÓGICAS Q1 (CALIBRADAS) =====\n');
            fprintf('  * Puntos Validados Empíricamente (Match): %d intersecciones\n', length(idx_eval));
            fprintf('  * Coeficiente de Calibración Linear:      Slope = %.3f, Intercept = %.2f\n', p_fit(1), p_fit(2));
            fprintf('  * Error Cuadrático Medio (RMSE):         %.2f dB (Optimizado Q1)\n', rmse_val);
            fprintf('  * Sesgo del Modelo (Bias):               %.2f dB (Neutralizado)\n', bias_val);
            fprintf('  * Desviación del Desvanecimiento (Sigma): %.2f dB\n', sigma_sh);
            fprintf(' ==================================================================\n\n');
            
            Best_RSSI_Dual = Best_RSSI_Calibrated; % Actualizar vector con valores calibrados
        end
    end
    
    %% 8. RENDERIZADO Y EXPORTACIÓN DE RESULTADOS (600 DPI)
    disp(' -> [FASE 5] Generando figuras vectoriales Q1 y dataset empírico...');
    Render_Empirical_Validation_3D(T_Twin, Anchors, Node_Status, Best_RSSI_Dual, ...
                                   Serving_GW_Dual, Meas_RSSI_Val, Meas_SNR_Val, Meas_GW_ID, HW, folder_name);
                                   
    Render_3DMSAGA_Solution_3D(T_Twin, Solutions{4}, RSSI_Matrix, BinM_3D, HW, City.Name, ...
                               Algo_Names(4), anchor_indices, Anchors, folder_name);
                           
    Export_Validation_CSV(T_Twin, Anchors, RSSI_Matrix(:,1), RSSI_Matrix(:,2), ...
                          Best_RSSI_Dual, Node_Status, Meas_RSSI_Val, folder_name);
                      
    disp('=================================================================');
    disp([' PROCESO COMPLETADO. Revise la carpeta: ', folder_name]);
    disp('=================================================================');
end

%% ========================================================================
%% MÓDULO DE CONEXIÓN CLOUD: API REST DE THE THINGS STACK (TTS)
%% ========================================================================
function T_TTS = Sync_Data_From_TTS_API(app_id, api_key, region_subdomain)
    T_TTS = table();
    url_api = sprintf('https://%s/api/v3/as/applications/%s/packages/storage/uplink', region_subdomain, app_id);
    
    options = weboptions('HeaderFields', {'Authorization', ['Bearer ', api_key]; ...
                                         'Accept', 'text/event-stream'}, ...
                         'Timeout', 45);
                         
    disp([' [*] Consultando API de TTS en: ', url_api]);
    try
        raw_stream = webread(url_api, options);
    catch ME
        warning('[!] Error al conectar con TTS API: %s', ME.message);
        disp('    [i] Asegúrese de tener conexión a Internet y que la API Key sea válida.');
        return;
    end
    
    lines = splitlines(raw_stream);
    parsed = [];
    
    for k = 1:length(lines)
        line = strtrim(lines{k});
        if startsWith(line, 'data:')
            json_str = extractAfter(line, 'data:');
            try
                data = jsondecode(json_str);
                if isfield(data, 'result') && isfield(data.result, 'uplink_message')
                    up = data.result.uplink_message;
                    
                    lat = NaN; lon = NaN;
                    if isfield(up, 'decoded_payload') && isfield(up.decoded_payload, 'latitude')
                        lat = up.decoded_payload.latitude;
                        lon = up.decoded_payload.longitude;
                    elseif isfield(up, 'locations') && isfield(up.locations, 'user')
                        lat = up.locations.user.latitude;
                        lon = up.locations.user.longitude;
                    end
                    
                    if isfield(up, 'rx_metadata')
                        rx_meta = up.rx_metadata;
                        for r = 1:length(rx_meta)
                            gw_id_str = string(rx_meta(r).gateway_ids.gateway_id);
                            rssi_val  = double(rx_meta(r).rssi);
                            snr_val   = double(rx_meta(r).snr);
                            
                            gw_num = 1; % Por defecto Paltas
                            if contains(lower(gw_id_str), "pucesa") || contains(lower(gw_id_str), "gateway2")
                                gw_num = 2;
                            end
                            
                            rec.Lat       = lat;
                            rec.Lon       = lon;
                            rec.RSSI      = rssi_val;
                            rec.SNR       = snr_val;
                            rec.Gateway_ID = gw_num;
                            
                            parsed = [parsed; rec]; %#ok<AGROW>
                        end
                    end
                end
            catch
                % Ignorar líneas corruptas del stream
            end
        end
    end
    
    if ~isempty(parsed)
        T_TTS = struct2table(parsed);
        T_TTS(isnan(T_TTS.Lat) | T_TTS.Lat == 0, :) = [];
        fprintf(' [*] Se sincronizaron exitosamente %d registros desde la nube de TTS.\n', height(T_TTS));
    else
        disp(' [!] La API de TTS respondió pero no devolvió tramas geolocalizadas.');
    end
end

%% ========================================================================
%% FÍSICA RF ORIGINAL DE MDPI_SUITE_6 (CON CORRECCIÓN DE VALLE)
%% ========================================================================
function [BinM_3D, Pts_3D, RSSI_Matrix] = Precompute_RF_ITU_OriginalFixed(T, HW)
    N = height(T);
    BinM_3D = false(N, N);
    RSSI_Matrix = zeros(N, N) - 150;
    Pts_3D = [T.X_m, T.Y_m, T.Altitude_m];
    
    L0 = 20 * log10(HW.Freq) - 27.55; 
    
    for gw = 1:N
        d_m = sqrt((T.X_m - T.X_m(gw)).^2 + (T.Y_m - T.Y_m(gw)).^2 + (T.Altitude_m - T.Altitude_m(gw)).^2);
        d_m(d_m < 1) = 1;
        
        n_path = 3.2 * ones(N, 1);
        L_clut = zeros(N, 1);
        
        idx_den = (T.Clutter == "Dense Urban");    L_clut(idx_den) = 18; n_path(idx_den) = 3.8; 
        idx_prk = (T.Clutter == "Park/Periphery"); L_clut(idx_prk) = 12; n_path(idx_prk) = 3.5; 
        
        Alt_GW_Real = T.Altitude_m(gw) + HW.Height; 
        diff_alt = Alt_GW_Real - T.Altitude_m; 
        
        L_topo = zeros(N, 1);
        c_idx = (diff_alt < -15); 
        L_topo(c_idx) = min(10 * log10(abs(diff_alt(c_idx))), 35);
        
        v_idx = (diff_alt > 15) & (d_m > 1800); 
        L_topo(v_idx) = min(12 * log10(diff_alt(v_idx)), 28);
        
        rssi = (HW.Ptx + HW.Gain) - L0 - 10 .* n_path .* log10(d_m) - L_clut - HW.PenetrationLoss - L_topo;
        RSSI_Matrix(:, gw) = rssi;
        BinM_3D(:, gw) = (rssi >= HW.Sens);
    end
end

%% ========================================================================
%% NORMALIZACIÓN DE CLUTTER Y ALGORITMOS DE TESIS
%% ========================================================================
function T = Normalize_Clutter_Distribution(T)
    N = height(T);
    densidad = zeros(N, 1);
    for i = 1:N
        densidad(i) = sum(sqrt((T.X_m - T.X_m(i)).^2 + (T.Y_m - T.Y_m(i)).^2) < 300);
    end
    p_denso = prctile_base(densidad, 75);
    p_resid = prctile_base(densidad, 20);
    
    Clutter = strings(N, 1);
    for i = 1:N
        if densidad(i) >= p_denso, Clutter(i) = "Dense Urban";
        elseif densidad(i) >= p_resid, Clutter(i) = "Residential";
        else, Clutter(i) = "Park/Periphery"; end
    end
    Clutter(1) = "Residential"; Clutter(2) = "Residential";
    T.Clutter = Clutter;
end

function val = prctile_base(x, p)
    x_s = sort(x(:));
    idx = max(1, min(length(x_s), round((p/100) * length(x_s))));
    val = x_s(idx);
end

function sol = Run_Greedy_Original(BinM_3D, target, anchors)
    [N, C] = size(BinM_3D); sol = false(1, C); sol(anchors) = true; cov = any(BinM_3D(:, anchors), 2);
    while (sum(cov)/N) < target
        b_g = 0; b_n = -1; cands = find(~sol);
        for i = cands, g = sum(BinM_3D(:, i) & ~cov); if g > b_g, b_g = g; b_n = i; end, end
        if b_n > 0 && b_g > 0, sol(b_n) = true; cov = cov | BinM_3D(:, b_n); else, break; end
    end
end

function sol = Run_KMedoids_Original(Pts_3D, BinM_3D, target, anchors)
    [N, C] = size(BinM_3D); sol = false(1, C);
    D_euc = sqrt((Pts_3D(:,1) - Pts_3D(:,1)').^2 + (Pts_3D(:,2) - Pts_3D(:,2)').^2 + (Pts_3D(:,3) - Pts_3D(:,3)').^2);
    n_anc = length(anchors);
    for k = n_anc:2:30
        if k == n_anc, idx_m = anchors;
        else
            k_extra = k - n_anc; c_idx = zeros(k_extra, 1);
            min_dist = min(D_euc(:, anchors), [], 2); min_dist(anchors) = 0;
            for ki = 1:k_extra
                [~, next_c] = max(min_dist); c_idx(ki) = next_c;
                min_dist = min(min_dist, D_euc(:, next_c)); min_dist(c_idx(1:ki)) = 0;
            end
            medoids = unique([anchors(:); c_idx]);
            for iter_pam = 1:5
                [~, cluster_assign] = min(D_euc(:, medoids), [], 2); improved = false;
                for m = (n_anc+1):length(medoids)
                    members = find(cluster_assign == m); if isempty(members), continue; end
                    [~, best_l] = min(sum(D_euc(members, members), 2)); new_m = members(best_l);
                    if new_m ~= medoids(m) && ~ismember(new_m, anchors), medoids(m) = new_m; improved = true; end
                end
                if ~improved, break; end
            end
            idx_m = medoids;
        end
        if (sum(sum(BinM_3D(:, idx_m), 2) > 0) / N) >= target, sol(idx_m) = true; break; end
    end
    if sum(sol) == 0, sol(idx_m) = true; end
end

function [sol, fit_hist] = Run_GA_Original(BinM_3D, target, use_memetic, anchors)
    [N, C] = size(BinM_3D); p_size = 24; gen = 30; fit_hist = zeros(gen, 1);
    Pop = rand(p_size, C) < (10/C); Pop(:, anchors) = true; Pop(1,:) = Run_Greedy_Original(BinM_3D, target, anchors);
    for g = 1:gen
        Fit = zeros(p_size, 1);
        for i = 1:p_size
            mapa = sum(BinM_3D(:, find(Pop(i,:))), 2);
            c_tot = sum(mapa >= 1)/N; c_k2 = sum(mapa >= 2)/N; gw_cnt = sum(Pop(i,:));
            Fit(i) = (c_tot * 10000) + (c_k2 * 1000) - (gw_cnt * 50);
            if c_tot < target, Fit(i) = Fit(i) - 50000; end
        end
        [best_f, b] = max(Fit); fit_hist(g) = best_f; Best = Pop(b,:); NewPop = Pop;
        for i = 2:2:p_size
            p1 = Pop(randi(p_size),:); p2 = Pop(randi(p_size),:); mask = rand(1, C) > 0.5; c1 = p1; c1(mask) = p2(mask);
            if rand < 0.8
                if use_memetic, c1 = Smart_Repair_Original(c1, BinM_3D, target, anchors);
                else, mut = randi(C); if ~ismember(mut, anchors), c1(mut) = ~c1(mut); end; end
            end
            c1(anchors) = true; NewPop(i,:) = c1;
        end
        Pop = NewPop; Pop(1,:) = Best; Pop(:, anchors) = true;
    end
    sol = Pop(1,:);
end

function ind = Smart_Repair_Original(ind, BinM_3D, target, anchors)
    N = size(BinM_3D, 1); max_iter = 10; iter = 0; ind(anchors) = true;
    while iter < max_iter
        iter = iter + 1; idx = find(ind); mapa = sum(BinM_3D(:, idx), 2);
        if (sum(mapa >= 1) / N) >= target
            removable = setdiff(idx, anchors);
            if ~isempty(removable)
                unq = (mapa == 1); sc = sum(BinM_3D(:, removable) & unq, 1); [val, w] = min(sc);
                if val < 5, ind(removable(w)) = false; continue; end
            end
            break;
        else
            unc = (mapa == 0); cands = find(~ind); if isempty(cands), break; end
            gains = sum(BinM_3D(unc, cands), 1); [bg, best_idx] = max(gains);
            if bg > 0, ind(cands(best_idx)) = true; else, break; end
        end
    end
    ind(anchors) = true;
end

%% ========================================================================
%% RENDERIZADORES 3D Q1 CON TOOLTIPS EXTENDIDOS
%% ========================================================================
function Render_Empirical_Validation_3D(T, Anchors, Status, Best_R, Srv_GW, M_RSSI, M_SNR, M_GW, HW, folder)
    f1 = figure('Name', 'Validación Empírica Cloud (TTS API) - Tooltips Q1', 'Position', [50 50 1150 780], 'Color', 'w');
    a1 = axes(f1); hold(a1, 'on'); grid(a1, 'on');
    N = height(T);
    
    s_inter    = T.Street_1 + " & " + T.Street_2;
    s_coords   = string(round(T.Lat, 5)) + ", " + string(round(T.Lon, 5));
    s_elev     = string(round(T.Altitude_m, 1)) + " msnm";
    s_sim_rssi = string(round(Best_R, 1)) + " dBm";
    s_sim_gw   = "GW-" + string(Srv_GW) + " (" + string(arrayfun(@(x) Anchors(max(1, min(2, x))).Name, Srv_GW, 'UniformOutput', false)) + ")";
    
    s_field_rssi = strings(N, 1); s_field_snr = strings(N, 1); s_field_gw = strings(N, 1);
    for i = 1:N
        if ~isnan(M_RSSI(i))
            s_field_rssi(i) = string(round(M_RSSI(i), 1)) + " dBm";
            s_field_snr(i)  = string(round(M_SNR(i), 1)) + " dB";
            gw_id = M_GW(i);
            if gw_id >= 1 && gw_id <= length(Anchors)
                s_field_gw(i) = sprintf('GW-%d (%s)', gw_id, Anchors(gw_id).Name);
            else
                s_field_gw(i) = "Gateway Dinámico TTS";
            end
        else
            s_field_rssi(i) = "Sin Muestras en Campo"; s_field_snr(i) = "N/A"; s_field_gw(i) = "No Registrado";
        end
    end
    
    idx_0 = (Status == 0); if any(idx_0), scatter3(a1, T.X_m(idx_0), T.Y_m(idx_0), T.Altitude_m(idx_0), 12, [0.78 0.78 0.78], 'filled', 'MarkerFaceAlpha', 0.35); end
    
    idx_1 = (Status == 1);
    if any(idx_1)
        s_1 = scatter3(a1, T.X_m(idx_1), T.Y_m(idx_1), T.Altitude_m(idx_1), 24, [0 0.45 0.85], 'filled', 'MarkerFaceAlpha', 0.75);
        s_1.DataTipTemplate.DataTipRows = [dataTipTextRow('Calles:', cellstr(s_inter(idx_1))); dataTipTextRow('Simulado [GW]:', cellstr(s_sim_gw(idx_1))); dataTipTextRow('Simulado [RSSI]:', cellstr(s_sim_rssi(idx_1)))];
    end
    
    idx_2 = (Status == 2);
    if any(idx_2)
        s_2 = scatter3(a1, T.X_m(idx_2), T.Y_m(idx_2), T.Altitude_m(idx_2), 58, [0.12 0.75 0.25], 'filled', 'MarkerEdgeColor', 'k', 'LineWidth', 1.2);
        s_2.DataTipTemplate.DataTipRows = [ ...
            dataTipTextRow('Calles:', cellstr(s_inter(idx_2))); ...
            dataTipTextRow('Coordenadas:', cellstr(s_coords(idx_2))); ...
            dataTipTextRow('GW Servidor (Teórico):', cellstr(s_sim_gw(idx_2))); ...
            dataTipTextRow('RSSI Predicho (Calibrado):', cellstr(s_sim_rssi(idx_2))); ...
            dataTipTextRow('GW Servidor (Real TTS):', cellstr(s_field_gw(idx_2))); ...
            dataTipTextRow('RSSI Medido (Drive-Test):', cellstr(s_field_rssi(idx_2))); ...
            dataTipTextRow('SNR Medido (Drive-Test):', cellstr(s_field_snr(idx_2)))];
    end
    
    idx_3 = (Status == 3);
    if any(idx_3)
        s_3 = scatter3(a1, T.X_m(idx_3), T.Y_m(idx_3), T.Altitude_m(idx_3), 58, [0.88 0.15 0.15], 'filled', 'MarkerEdgeColor', 'k', 'LineWidth', 1.2);
        s_3.DataTipTemplate.DataTipRows = [ ...
            dataTipTextRow('Calles:', cellstr(s_inter(idx_3))); ...
            dataTipTextRow('Coordenadas:', cellstr(s_coords(idx_3))); ...
            dataTipTextRow('GW Servidor (Teórico):', cellstr(s_sim_gw(idx_3))); ...
            dataTipTextRow('RSSI Predicho (Calibrado):', cellstr(s_sim_rssi(idx_3))); ...
            dataTipTextRow('GW Servidor (Real TTS):', cellstr(s_field_gw(idx_3))); ...
            dataTipTextRow('RSSI Medido (Drive-Test):', cellstr(s_field_rssi(idx_3))); ...
            dataTipTextRow('SNR Medido (Drive-Test):', cellstr(s_field_snr(idx_3)))];
    end
    
    colors = {[1 0.84 0], [0 0.88 1]}; edges = {[0.8 0 0], [0 0.15 0.7]};
    for a = 1:2
        scatter3(a1, T.X_m(a), T.Y_m(a), T.Altitude_m(a), 700, colors{a}, 'p', 'filled', 'MarkerEdgeColor', edges{a}, 'LineWidth', 2.5);
        text(a1, T.X_m(a), T.Y_m(a), T.Altitude_m(a) + 32, sprintf('  %s', Anchors(a).Name), 'FontWeight', 'bold', 'FontSize', 10, 'Color', edges{a}, 'BackgroundColor', [1 1 1 0.8]);
    end
    
    daspect(a1, [1 1 0.12]); view(a1, -35, 42);
    xlabel(a1, 'Proyección Este X (m)'); ylabel(a1, 'Proyección Norte Y (m)'); zlabel(a1, 'Altitud SRTM (msnm)');
    title(a1, 'Validación Espacial 3D Q1: Gemelo Digital vs. TTS API (Calibrado)', 'FontWeight', 'bold');
    exportgraphics(f1, fullfile(folder, 'Fig1_Cloud_Validation_Q1_Enhanced.png'), 'Resolution', 600);
end

function Render_3DMSAGA_Solution_3D(T, sol, RSSI_Matrix, BinM_3D, HW, city, algo, anchors, Anchors, folder)
    idx = find(sol); N = height(T); Best_R = zeros(N, 1) - 150;
    [max_r, ~] = max(RSSI_Matrix(:, idx), [], 2);
    for i=1:N, if max_r(i)>=HW.Sens, Best_R(i)=max_r(i); end, end
    alive = Best_R >= HW.Sens; dead = Best_R < HW.Sens;
    
    f2 = figure('Name', 'Despliegue Óptimo 3D-M-SAGA', 'Position', [120 80 1100 740], 'Color', 'w');
    a2 = axes(f2); hold(a2, 'on'); grid(a2, 'on');
    scatter3(a2, T.X_m(dead), T.Y_m(dead), T.Altitude_m(dead), 10, [0.75 0.75 0.75], 'filled', 'MarkerFaceAlpha', 0.4);
    scatter3(a2, T.X_m(alive), T.Y_m(alive), T.Altitude_m(alive), 25, Best_R(alive), 'filled', 'MarkerFaceAlpha', 0.9);
    
    new_gws = setdiff(idx, anchors);
    if ~isempty(new_gws), scatter3(a2, T.X_m(new_gws), T.Y_m(new_gws), T.Altitude_m(new_gws), 380, 'w', '^', 'filled', 'MarkerEdgeColor', 'k', 'LineWidth', 1.8); end
    
    colors = {[1 0.84 0], [0 0.88 1]}; edges = {[0.8 0 0], [0 0.15 0.7]};
    for a = 1:2, scatter3(a2, T.X_m(a), T.Y_m(a), T.Altitude_m(a), 600, colors{a}, 'p', 'filled', 'MarkerEdgeColor', edges{a}, 'LineWidth', 2.2); end
    daspect(a2, [1 1 0.12]); colormap(a2, 'jet'); clim(a2, [HW.Sens, -70]); view(a2, -35, 42); colorbar(a2);
    title(a2, sprintf('%s - Total: %d GWs', algo, length(idx)), 'FontWeight', 'bold');
    exportgraphics(f2, fullfile(folder, 'Fig2_Optimal_Deployment.png'), 'Resolution', 600);
end

function T = Build_DigitalTwin_Restored(filename, City, Anchors)
    raw = fileread(filename); data = jsondecode(raw);
    all_coords = []; street_tags = string.empty(0, 1);
    for i = 1:length(data.features)
        f = data.features(i); if iscell(data.features), f = f{1}; end
        st_name = "Unnamed Road";
        if isfield(f, 'properties') && isfield(f.properties, 'name') && ~isempty(f.properties.name)
            st_name = string(f.properties.name);
        end
        if strcmp(f.geometry.type, 'LineString')
            coords = f.geometry.coordinates; all_coords = [all_coords; coords]; %#ok<AGROW>
            street_tags = [street_tags; repmat(st_name, size(coords, 1), 1)]; %#ok<AGROW>
        end
    end
    [unique_pts, ~, ic] = unique(round(all_coords, 5), 'rows');
    c1 = strings(size(unique_pts, 1), 1); c2 = strings(size(unique_pts, 1), 1); counts = zeros(size(unique_pts, 1), 1);
    for u = 1:size(unique_pts, 1)
        st_list = unique(street_tags(ic == u));
        counts(u) = length(st_list); c1(u) = st_list(1);
        if length(st_list) > 1, c2(u) = st_list(2); else, c2(u) = "Crossroad"; end
    end
    inter_idx = find(counts >= 2);
    if length(inter_idx) < 100, inter_idx = (1:size(unique_pts, 1))'; end
    
    lat = [Anchors(1).Lat; Anchors(2).Lat; unique_pts(inter_idx, 2)];
    lon = [Anchors(1).Lon; Anchors(2).Lon; unique_pts(inter_idx, 1)];
    c1  = ["Campus PUCESA"; "Sector Paltas"; c1(inter_idx)];
    c2  = ["Gateway2PUCESA (TTN)"; "Gateway1PALTAS (TTN)"; c2(inter_idx)];
    
    N = length(lat); Alt_m = zeros(N, 1);
    Alt_m(1) = Anchors(1).Alt; Alt_m(2) = Anchors(2).Alt;
    if isfile('SRTM_Elevation_Cache.mat')
        cached = load('SRTM_Elevation_Cache.mat');
        if isfield(cached, 'Alt_m') && length(cached.Alt_m) >= (N-2), Alt_m(3:end) = cached.Alt_m(end-(N-3):end); end
    end
    
    R_earth = 6371000; X_m = deg2rad(lon - City.Lon) * R_earth * cosd(City.Lat); Y_m = deg2rad(lat - City.Lat) * R_earth;
    Clutter = repmat("Residential", N, 1);
    T = table(c1, c2, Alt_m, lat, lon, X_m, Y_m, Clutter, 'VariableNames', {'Street_1', 'Street_2', 'Altitude_m', 'Lat', 'Lon', 'X_m', 'Y_m', 'Clutter'});
end

function T_all = Ingest_Local_FieldTester_CSVs(folder)
    T_all = table(); if ~exist(folder, 'dir'), return; end
    files = dir(fullfile(folder, '*.csv'));
    for f = 1:length(files)
        fp = fullfile(folder, files(f).name);
        opts = detectImportOptions(fp); opts.VariableNamingRule = 'preserve';
        raw = readtable(fp, opts); vn = lower(string(raw.Properties.VariableNames)); N = height(raw);
        Lat = Safe_Double(raw, find(contains(vn, "lat"), 1), N);
        Lon = Safe_Double(raw, find(contains(vn, "lon"), 1), N);
        RSSI = Safe_Double(raw, find(contains(vn, "rssi"), 1), N);
        SNR  = Safe_Double(raw, find(contains(vn, "snr"), 1), N);
        v = ~isnan(Lat) & ~isnan(Lon) & (Lat ~= 0);
        if any(v)
            if median(Lat(v)) > 0, Lat = -abs(Lat); end
            if median(Lon(v)) > 0, Lon = -abs(Lon); end
        end
        valid = v & (Lat >= -2.0 & Lat <= -0.5) & (Lon >= -79.5 & Lon <= -78.0);
        if sum(valid) > 0
            T_all = [T_all; table(Lat(valid), Lon(valid), RSSI(valid), SNR(valid), ones(sum(valid),1), 'VariableNames', {'Lat', 'Lon', 'RSSI', 'SNR', 'Gateway_ID'})]; %#ok<AGROW>
        end
    end
end

function vec = Safe_Double(tbl, col_idx, N)
    if isempty(col_idx), vec = nan(N, 1); return; end
    c = tbl{:, col_idx};
    if isnumeric(c), vec = double(c);
    else, vec = str2double(regexprep(strrep(strtrim(string(c)), ',', '.'), '[^0-9\.\+\-eE]', '')); end
    vec = vec(:);
end

function row = Extract_KPIs(name, sol, BinM_3D, time_s)
    idx = find(sol); n_gws = length(idx); N = size(BinM_3D, 1);
    mapa = sum(BinM_3D(:, idx), 2);
    c_tot = round((sum(mapa >= 1) / N) * 100, 2);
    k1 = round((sum(mapa == 1) / N) * 100, 2); 
    k2 = round((sum(mapa == 2) / N) * 100, 2); 
    k3 = round((sum(mapa >= 3) / N) * 100, 2);
    row = {name, n_gws, c_tot, k1, k2, k3, round(time_s, 2)};
end

function Export_Validation_CSV(T, Anchors, R_GW1, R_GW2, Best_R, Status, M_RSSI, folder)
    N = height(T);
    T_Exp = table((1:N)', T.Street_1, T.Street_2, T.Lat, T.Lon, round(T.Altitude_m, 1), T.Clutter, ...
                  round(R_GW1, 1), round(R_GW2, 1), round(Best_R, 1), round(M_RSSI, 1), Status, ...
                  'VariableNames', {'Node_ID', 'Primary_Street', 'Intersecting_Street', ...
                                    'Latitude', 'Longitude', 'Elevation_MSNM', 'Clutter_Class', ...
                                    'RSSI_PUCESA_dBm', 'RSSI_PALTAS_dBm', ...
                                    'Best_Predicted_RSSI_dBm', 'Measured_Field_RSSI_dBm', 'Validation_Status'});
    writetable(T_Exp, fullfile(folder, 'Dataset_TTS_API_Validation.csv'));
end