% scripts/generate_phase5b_pilot_plots.m
% Generates publication-quality validation figures for Phase 5B Pilot Report.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
raw_dir = fullfile(project_root, 'data', 'ieee9bus_60hz_phase5b_pilot', 'raw');
fig_dir = fullfile(project_root, 'docs', 'figures', 'phase5b_pilot');
if ~exist(fig_dir, 'dir')
    mkdir(fig_dir);
end

% Set figure invisible for batch export
set(0, 'DefaultFigureVisible', 'off');

%% Figure 1: 8-Class Three-Phase Voltage Waveforms (200 ms)
fig1 = figure('Position', [100, 100, 1200, 1400], 'Color', 'w');

representative_files = {
    'P5B_NORM_0001_nominal_baseline.mat', 'Normal (Nominal Baseline)';
    'P5B_SAG_0001_3p_moderate_nom.mat',   'Voltage Sag (3P Moderate, Res: 0.73 pu)';
    'P5B_SWL_0001_3p_moderate_nom.mat',   'Voltage Swell (3P Switched Cap 150 MVAR)';
    'P5B_INT_0001_3p_standard_nom.mat',   'Interruption (3P Breaker Isolation)';
    'P5B_HAR_0001_3p_typical_h3h5h7.mat', 'Harmonics (3P 6-Pulse H3, H5, H7)';
    'P5B_FLK_0001_3p_fm8p8hz_peak.mat',   'Flicker (3P Envelope Modulation 8.8 Hz)';
    'P5B_NOT_0001_3p_w600us_rep1.mat',    'Notch (3P Commutation 600 us, 150 ohm)';
    'P5B_TRN_0001_3p_l2_c8_r08.mat',      'Transient (3P Switched RLC, f~1.26 kHz)'
};

colors = [0.12 0.47 0.71; 0.20 0.63 0.17; 0.89 0.10 0.11]; % Blue, Green, Red for A, B, C

for k = 1:8
    mat_file = fullfile(raw_dir, representative_files{k, 1});
    d = load(mat_file);
    t_ms = (0:999) * (1000 / 5000); % 0 to 200 ms
    V = d.V_frame;
    
    subplot(4, 2, k);
    plot(t_ms, V(:, 1), 'Color', colors(1, :), 'LineWidth', 1.0); hold on;
    plot(t_ms, V(:, 2), 'Color', colors(2, :), 'LineWidth', 1.0);
    plot(t_ms, V(:, 3), 'Color', colors(3, :), 'LineWidth', 1.0);
    hold off;
    grid on;
    xlim([0 200]);
    ylim([-1.6 1.6]);
    title(sprintf('(%s) %s', char(64+k), representative_files{k, 2}), 'FontSize', 11, 'FontWeight', 'bold');
    xlabel('Time (ms)', 'FontSize', 9);
    ylabel('Voltage (pu)', 'FontSize', 9);
    if k == 1
        legend('Phase A', 'Phase B', 'Phase C', 'Location', 'northeast', 'FontSize', 8);
    end
end

exportgraphics(fig1, fullfile(fig_dir, 'pilot_8class_waveforms.png'), 'Resolution', 300);
close(fig1);
fprintf('[Success] Saved %s\n', fullfile(fig_dir, 'pilot_8class_waveforms.png'));

%% Figure 2: Asymmetrical vs Symmetrical Multiphase RMS Profiles
fig2 = figure('Position', [100, 100, 1200, 900], 'Color', 'w');

cases = {
    'P5B_SAG_0001_3p_moderate_nom.mat',   'Sag: Symmetrical 3-Phase (All Depressed)';
    'P5B_SAG_0002_1p_deep_light.mat',     'Sag: Single-Phase A (Phase A Depressed to 0.45 pu)';
    'P5B_SAG_0003_2p_phAB_challenge.mat', 'Sag: Phase-to-Phase AB (Phases A & B Depressed)';
    'P5B_NOT_0001_3p_w600us_rep1.mat',    'Notch: 3-Phase Commutation Notching';
    'P5B_NOT_0002_2p_w500us_rep2.mat',    'Notch: 2-Phase Commutation (AB)';
    'P5B_NOT_0003_1p_w800us_challenge.mat','Notch: 1-Phase Commutation (Phase A with Ground Return)'
};

for k = 1:6
    mat_file = fullfile(raw_dir, cases{k, 1});
    d = load(mat_file);
    V = d.V_frame;
    
    % Compute half-cycle windowed RMS (42 samples at 5 kHz)
    w_len = 42;
    n_pts = 1000 - w_len + 1;
    rms_a = zeros(n_pts, 1); rms_b = zeros(n_pts, 1); rms_c = zeros(n_pts, 1);
    t_rms = (0:n_pts-1) * (1000 / 5000) + (w_len/2)*(1000/5000);
    for idx = 1:n_pts
        rms_a(idx) = sqrt(mean(V(idx:idx+w_len-1, 1).^2));
        rms_b(idx) = sqrt(mean(V(idx:idx+w_len-1, 2).^2));
        rms_c(idx) = sqrt(mean(V(idx:idx+w_len-1, 3).^2));
    end
    
    subplot(2, 3, k);
    plot(t_rms, rms_a, 'Color', colors(1, :), 'LineWidth', 1.3); hold on;
    plot(t_rms, rms_b, 'Color', colors(2, :), 'LineWidth', 1.3);
    plot(t_rms, rms_c, 'Color', colors(3, :), 'LineWidth', 1.3);
    yline(0.5887, '--k', 'Nominal (0.589 pu)', 'LabelHorizontalAlignment', 'left', 'FontSize', 8);
    hold off;
    grid on;
    xlim([0 200]);
    ylim([0.15 0.75]);
    title(sprintf('(%s) %s', char(64+k), cases{k, 2}), 'FontSize', 10, 'FontWeight', 'bold');
    xlabel('Time (ms)', 'FontSize', 9);
    ylabel('Half-Cycle RMS (pu)', 'FontSize', 9);
    if k == 1
        legend('RMS A', 'RMS B', 'RMS C', 'Location', 'southwest', 'FontSize', 8);
    end
end

exportgraphics(fig2, fullfile(fig_dir, 'pilot_multiphase_rms_comparison.png'), 'Resolution', 300);
close(fig2);
fprintf('[Success] Saved %s\n', fullfile(fig_dir, 'pilot_multiphase_rms_comparison.png'));

%% Figure 3: Spectral & FFT Analysis
fig3 = figure('Position', [100, 100, 1200, 800], 'Color', 'w');

spec_cases = {
    'P5B_NORM_0001_nominal_baseline.mat',      'Normal (Pure 60 Hz)';
    'P5B_HAR_0001_3p_typical_h3h5h7.mat',      'Harmonics (H3=180Hz, H5=300Hz, H7=420Hz)';
    'P5B_HAR_0003_3p_full_odd_challenge.mat',  'Harmonics Challenge (H3 to H11 Odd Spectrum)';
    'P5B_FLK_0001_3p_fm8p8hz_peak.mat',        'Flicker (60 Hz Carrier +/- 8.8 Hz Sidebands)'
};

for k = 1:4
    mat_file = fullfile(raw_dir, spec_cases{k, 1});
    d = load(mat_file);
    va = d.V_frame(:, 1);
    
    fs = 5000;
    N = 1000;
    f_vec = (0:N/2) * (fs / N);
    Y = fft(va) / N;
    mag = 2 * abs(Y(1:N/2+1));
    
    subplot(2, 2, k);
    if k <= 3
        stem(f_vec, mag, 'Marker', 'none', 'LineWidth', 1.2, 'Color', [0.12 0.47 0.71]);
        xlim([0 1000]);
        ylim([0 1.0]);
        xlabel('Frequency (Hz)', 'FontSize', 9);
        ylabel('Voltage Magnitude (pu)', 'FontSize', 9);
    else
        % Zoomed in for flicker sidebands around 60 Hz
        plot(f_vec, mag, 'LineWidth', 1.2, 'Color', [0.89 0.10 0.11]);
        xlim([30 90]);
        ylim([0 0.9]);
        xlabel('Frequency (Hz) [Zoomed around 60 Hz]', 'FontSize', 9);
        ylabel('Voltage Magnitude (pu)', 'FontSize', 9);
    end
    grid on;
    title(sprintf('(%s) %s', char(64+k), spec_cases{k, 2}), 'FontSize', 10, 'FontWeight', 'bold');
end

exportgraphics(fig3, fullfile(fig_dir, 'pilot_spectral_analysis.png'), 'Resolution', 300);
close(fig3);
fprintf('[Success] Saved %s\n', fullfile(fig_dir, 'pilot_spectral_analysis.png'));

%% Figure 4: Bus 5 Current Waveforms (Iabc)
fig4 = figure('Position', [100, 100, 1200, 800], 'Color', 'w');

curr_cases = {
    'P5B_NORM_0001_nominal_baseline.mat', 'Normal Bus 5 Steady-State Load Current';
    'P5B_SAG_0001_3p_moderate_nom.mat',   'Sag: High Fault Inrush Current During Fault';
    'P5B_INT_0001_3p_standard_nom.mat',   'Interruption: Current Drops to Zero on Line Breaker Open';
    'P5B_TRN_0001_3p_l2_c8_r08.mat',      'Transient: High-Frequency Damped Ringing Current'
};

for k = 1:4
    mat_file = fullfile(raw_dir, curr_cases{k, 1});
    d = load(mat_file);
    t_ms = (0:999) * (1000 / 5000);
    I = d.I_frame;
    
    subplot(2, 2, k);
    plot(t_ms, I(:, 1), 'Color', colors(1, :), 'LineWidth', 1.0); hold on;
    plot(t_ms, I(:, 2), 'Color', colors(2, :), 'LineWidth', 1.0);
    plot(t_ms, I(:, 3), 'Color', colors(3, :), 'LineWidth', 1.0);
    hold off;
    grid on;
    xlim([0 200]);
    title(sprintf('(%s) %s', char(64+k), curr_cases{k, 2}), 'FontSize', 10, 'FontWeight', 'bold');
    xlabel('Time (ms)', 'FontSize', 9);
    ylabel('Current (pu / A)', 'FontSize', 9);
    if k == 1
        legend('Phase A', 'Phase B', 'Phase C', 'Location', 'northeast', 'FontSize', 8);
    end
end

exportgraphics(fig4, fullfile(fig_dir, 'pilot_current_waveforms.png'), 'Resolution', 300);
close(fig4);
fprintf('[Success] Saved %s\n', fullfile(fig_dir, 'pilot_current_waveforms.png'));

fprintf('\n[All Phase 5B Pilot Figures Generated Successfully!]\n');
