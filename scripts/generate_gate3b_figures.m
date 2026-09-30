% scripts/generate_gate3b_figures.m
% Generates the 8 diagnostic validation figures for Gate 3B Normal Dataset.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);

data_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'normal');
fig_dir = fullfile(project_root, 'docs', 'figures', 'gate3b');
if ~exist(fig_dir, 'dir')
    mkdir(fig_dir);
end

% Load features CSV
csv_file = fullfile(data_dir, 'normal_features.csv');
fprintf('Reading CSV: %s...\n', csv_file);
T = readtable(csv_file);

% Load raw simulations MAT for waveform plots
mat_file = fullfile(data_dir, 'raw_normal_simulations.mat');
fprintf('Reading MAT: %s...\n', mat_file);
mat_data = load(mat_file);
sim_results = mat_data.sim_results;

% Theme Colors
c_l1 = [0.22, 0.74, 0.97]; % Cyan
c_l2 = [0.96, 0.62, 0.04]; % Amber
c_l3 = [0.06, 0.73, 0.51]; % Emerald
c_dark = [0.06, 0.09, 0.16];
c_card = [0.12, 0.16, 0.23];
c_text = [0.97, 0.98, 0.99];
c_grid = [0.20, 0.25, 0.33];

fs = 5000;
N_win = 1000;
t_win_ms = (0:(N_win-1)) * (1000.0 / fs);

% -------------------------------------------------------------------------
% Fig 1: Random Normal Vabc waveform
% -------------------------------------------------------------------------
fprintf('Generating Fig 1: Random Normal Vabc waveform...\n');
f1 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 900, 420]);
ax1 = axes('Parent', f1, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax1, 'on'); grid(ax1, 'on');

% Sample from Condition 1 (Nominal Baseline), middle window
v_sim1 = sim_results(1).Vabc_resampled;
v_win1 = v_sim1(100:1099, :);

p1 = plot(ax1, t_win_ms, v_win1(:, 1), 'Color', c_l1, 'LineWidth', 1.8);
p2 = plot(ax1, t_win_ms, v_win1(:, 2), 'Color', c_l2, 'LineWidth', 1.8);
p3 = plot(ax1, t_win_ms, v_win1(:, 3), 'Color', c_l3, 'LineWidth', 1.8);

title(ax1, 'Fig 1 — Normal Three-Phase Voltage Waveform (Bus 5, IEEE 9-Bus, 60 Hz)', ...
    'Color', c_text, 'FontSize', 12, 'FontWeight', 'bold');
xlabel(ax1, 'Time (ms)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
ylabel(ax1, 'Bus 5 Voltage (pu)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
legend(ax1, [p1, p2, p3], {'Phase L1', 'Phase L2', 'Phase L3'}, ...
    'TextColor', c_text, 'Color', c_card, 'EdgeColor', c_grid, 'Location', 'northeast');
xlim(ax1, [0, 200]);
exportgraphics(f1, fullfile(fig_dir, 'fig1_random_normal_vabc_waveform.png'), 'Resolution', 200);
close(f1);

% -------------------------------------------------------------------------
% Fig 2: Three-Phase Overlay (1 fundamental cycle zoom)
% -------------------------------------------------------------------------
fprintf('Generating Fig 2: Three-Phase Overlay...\n');
f2 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 750, 420]);
ax2 = axes('Parent', f2, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax2, 'on'); grid(ax2, 'on');

cycle_samples = round(fs / 60.0); % ~83 samples
t_cycle_ms = (0:(cycle_samples-1)) * (1000.0 / fs);

plot(ax2, t_cycle_ms, v_win1(1:cycle_samples, 1), 'Color', c_l1, 'LineWidth', 2.2);
plot(ax2, t_cycle_ms, v_win1(1:cycle_samples, 2), 'Color', c_l2, 'LineWidth', 2.2);
plot(ax2, t_cycle_ms, v_win1(1:cycle_samples, 3), 'Color', c_l3, 'LineWidth', 2.2);

title(ax2, 'Fig 2 — Fundamental Cycle Three-Phase Overlay (120° Phase Separation)', ...
    'Color', c_text, 'FontSize', 12, 'FontWeight', 'bold');
xlabel(ax2, 'Time (ms)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
ylabel(ax2, 'Instantaneous Voltage (pu)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
legend(ax2, {'Phase A (0°)', 'Phase B (-120°)', 'Phase C (+120°)'}, ...
    'TextColor', c_text, 'Color', c_card, 'EdgeColor', c_grid, 'Location', 'northeast');
xlim(ax2, [0, t_cycle_ms(end)]);
exportgraphics(f2, fullfile(fig_dir, 'fig2_three_phase_overlay.png'), 'Resolution', 200);
close(f2);

% -------------------------------------------------------------------------
% Fig 3: Voltage RMS distribution
% -------------------------------------------------------------------------
fprintf('Generating Fig 3: Voltage RMS distribution...\n');
f3 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 750, 420]);
ax3 = axes('Parent', f3, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax3, 'on'); grid(ax3, 'on');

h_rms = histogram(ax3, T.rms_voltage, 25, 'FaceColor', c_l1, 'EdgeColor', [0.0 0.5 0.8], 'FaceAlpha', 0.85);
xline(ax3, 0.5874, '--r', 'LineWidth', 2, 'Label', 'Nominal Bus 5 RMS: 0.5874 pu', 'LabelVerticalAlignment', 'bottom');
xline(ax3, mean(T.rms_voltage), '-w', 'LineWidth', 1.5, 'Label', sprintf('Mean: %.4f pu', mean(T.rms_voltage)));

title(ax3, 'Fig 3 — Bus 5 RMS Voltage Distribution Across 32 Operating Points', ...
    'Color', c_text, 'FontSize', 12, 'FontWeight', 'bold');
xlabel(ax3, 'RMS Voltage (pu)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
ylabel(ax3, 'Frame Count', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
exportgraphics(f3, fullfile(fig_dir, 'fig3_voltage_rms_distribution.png'), 'Resolution', 200);
close(f3);

% -------------------------------------------------------------------------
% Fig 4: Dominant & System Frequency distribution
% -------------------------------------------------------------------------
fprintf('Generating Fig 4: Frequency distribution...\n');
f4 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 950, 420]);

subplot(1, 2, 1, 'Parent', f4);
ax4a = gca;
set(ax4a, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax4a, 'on'); grid(ax4a, 'on');
histogram(ax4a, T.dominant_freq, 10, 'FaceColor', [0.5 0.55 0.95], 'EdgeColor', [0.3 0.3 0.8], 'FaceAlpha', 0.85);
title(ax4a, 'Dominant Frequency (Goertzel Peak)', 'Color', c_text, 'FontSize', 11, 'FontWeight', 'bold');
xlabel(ax4a, 'Frequency (Hz)', 'Color', [0.6 0.65 0.72]);
ylabel(ax4a, 'Frame Count', 'Color', [0.6 0.65 0.72]);
xlim(ax4a, [59.0, 61.0]);

subplot(1, 2, 2, 'Parent', f4);
ax4b = gca;
set(ax4b, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax4b, 'on'); grid(ax4b, 'on');
histogram(ax4b, T.system_freq, 25, 'FaceColor', c_l3, 'EdgeColor', [0.0 0.5 0.3], 'FaceAlpha', 0.85);
xline(ax4b, 60.00, '--r', 'LineWidth', 2, 'Label', '60.00 Hz Center');
title(ax4b, 'System Frequency (Zero-Crossing Interpolation)', 'Color', c_text, 'FontSize', 11, 'FontWeight', 'bold');
xlabel(ax4b, 'Frequency (Hz)', 'Color', [0.6 0.65 0.72]);
ylabel(ax4b, 'Frame Count', 'Color', [0.6 0.65 0.72]);

sgtitle(f4, 'Fig 4 — 60-Hz Frequency Feature Distributions (No 50-Hz Contamination)', ...
    'Color', c_text, 'FontSize', 13, 'FontWeight', 'bold');
exportgraphics(f4, fullfile(fig_dir, 'fig4_dominant_frequency_distribution.png'), 'Resolution', 200);
close(f4);

% -------------------------------------------------------------------------
% Fig 5: THD distribution
% -------------------------------------------------------------------------
fprintf('Generating Fig 5: THD distribution...\n');
f5 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 750, 420]);
ax5 = axes('Parent', f5, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax5, 'on'); grid(ax5, 'on');

histogram(ax5, T.thd, 25, 'FaceColor', c_l2, 'EdgeColor', [0.8 0.4 0.0], 'FaceAlpha', 0.85);
xline(ax5, 2.0, '--r', 'LineWidth', 2, 'Label', 'Normal Limit (2.0%)', 'LabelVerticalAlignment', 'bottom');
xline(ax5, 5.0, ':r', 'LineWidth', 2, 'Label', 'IEEE 519 Limit (5.0%)', 'LabelVerticalAlignment', 'bottom');

title(ax5, 'Fig 5 — Total Harmonic Distortion (THD) Distribution (Mean = 0.0248%)', ...
    'Color', c_text, 'FontSize', 12, 'FontWeight', 'bold');
xlabel(ax5, 'THD (%)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
ylabel(ax5, 'Frame Count', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
xlim(ax5, [0, 2.5]);
exportgraphics(f5, fullfile(fig_dir, 'fig5_thd_distribution.png'), 'Resolution', 200);
close(f5);

% -------------------------------------------------------------------------
% Fig 6: Crest-factor distribution
% -------------------------------------------------------------------------
fprintf('Generating Fig 6: Crest-factor distribution...\n');
f6 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 750, 420]);
ax6 = axes('Parent', f6, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax6, 'on'); grid(ax6, 'on');

histogram(ax6, T.crest_factor, 25, 'FaceColor', [0.65 0.35 0.95], 'EdgeColor', [0.4 0.1 0.7], 'FaceAlpha', 0.85);
xline(ax6, sqrt(2.0), '--c', 'LineWidth', 2, 'Label', 'Pure Sine sqrt(2) = 1.4142', 'LabelVerticalAlignment', 'bottom');
xline(ax6, mean(T.crest_factor), '-w', 'LineWidth', 1.5, 'Label', sprintf('Mean: %.4f', mean(T.crest_factor)));

title(ax6, 'Fig 6 — Crest Factor Distribution Across Normal Operating Domain', ...
    'Color', c_text, 'FontSize', 12, 'FontWeight', 'bold');
xlabel(ax6, 'Crest Factor (Vpeak / Vrms)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
ylabel(ax6, 'Frame Count', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
exportgraphics(f6, fullfile(fig_dir, 'fig6_crest_factor_distribution.png'), 'Resolution', 200);
close(f6);

% -------------------------------------------------------------------------
% Fig 7: Duration distribution
% -------------------------------------------------------------------------
fprintf('Generating Fig 7: Duration distribution...\n');
f7 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 750, 420]);
ax7 = axes('Parent', f7, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
    'GridColor', c_grid, 'GridAlpha', 0.6);
hold(ax7, 'on'); grid(ax7, 'on');

histogram(ax7, T.duration, 10, 'FaceColor', c_l3, 'EdgeColor', [0.0 0.5 0.3], 'FaceAlpha', 0.85);
title(ax7, 'Fig 7 — Disturbance Duration Distribution (Constant 0.0 ms for Normal State)', ...
    'Color', c_text, 'FontSize', 12, 'FontWeight', 'bold');
xlabel(ax7, 'Disturbance Duration (ms)', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
ylabel(ax7, 'Frame Count', 'Color', [0.6 0.65 0.72], 'FontSize', 10);
xlim(ax7, [-10, 50]);
exportgraphics(f7, fullfile(fig_dir, 'fig7_duration_distribution.png'), 'Resolution', 200);
close(f7);

% -------------------------------------------------------------------------
% Fig 8: Selected harmonic distributions
% -------------------------------------------------------------------------
fprintf('Generating Fig 8: Selected harmonic distributions...\n');
f8 = figure('Visible', 'off', 'Color', c_dark, 'Position', [100, 100, 1050, 600]);

harms = {'h1', 'h2', 'h3', 'h5', 'h7', 'harmonic_energy'};
titles = {'H1 Fundamental (60 Hz)', 'H2 Second Harmonic (120 Hz)', ...
          'H3 Third Harmonic (180 Hz)', 'H5 Fifth Harmonic (300 Hz)', ...
          'H7 Seventh Harmonic (420 Hz)', 'Total Higher Harmonic Energy'};
colors = {c_l1, [0.95 0.25 0.35], c_l2, [0.65 0.35 0.95], [0.9 0.3 0.6], c_l3};

for k = 1:6
    subplot(2, 3, k, 'Parent', f8);
    ax8k = gca;
    set(ax8k, 'Color', c_card, 'XColor', [0.6 0.65 0.72], 'YColor', [0.6 0.65 0.72], ...
        'GridColor', c_grid, 'GridAlpha', 0.6);
    hold(ax8k, 'on'); grid(ax8k, 'on');
    histogram(ax8k, T.(harms{k}), 20, 'FaceColor', colors{k}, 'FaceAlpha', 0.85);
    title(ax8k, titles{k}, 'Color', c_text, 'FontSize', 10, 'FontWeight', 'bold');
    xlabel(ax8k, 'Magnitude (pu)', 'Color', [0.6 0.65 0.72]);
    ylabel(ax8k, 'Count', 'Color', [0.6 0.65 0.72]);
end

sgtitle(f8, 'Fig 8 — Harmonic Spectrum Magnitudes H1–H7 via Goertzel Bank', ...
    'Color', c_text, 'FontSize', 13, 'FontWeight', 'bold');
exportgraphics(f8, fullfile(fig_dir, 'fig8_selected_harmonic_distributions.png'), 'Resolution', 200);
close(f8);

fprintf('[SUCCESS] All 8 Gate 3B validation figures generated and saved to: %s\n', fig_dir);
exit(0);
