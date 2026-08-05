/* ==========================================================================
   MINIMALISM UI LOGIC — PQD DASHBOARD & MOBILE APP CONTROLLER
   ========================================================================== */

let currentViewMode = 'web';
let waveformChart = null;
let currentDisturbance = 'Normal';
let eventHistory = [];

const STATUS_COLORS = {
  'Normal': '#10b981',
  'Sag': '#f59e0b',
  'Swell': '#ef4444',
  'Harmonics': '#8b5cf6',
  'Transient': '#ec4899',
  'Interruption': '#dc2626',
  'Flicker': '#06b6d4',
  'Notch': '#eab308'
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  initWaveformChart();
  seedInitialEvents();
  startWaveformAnimation();
});

// View Mode Switcher (Web vs Mobile Simulator)
function switchView(mode) {
  currentViewMode = mode;
  const webDash = document.getElementById('web-dashboard');
  const mobileSim = document.getElementById('mobile-simulator');
  const btnWeb = document.getElementById('view-web-btn');
  const btnMobile = document.getElementById('view-mobile-btn');

  if (mode === 'web') {
    webDash.style.display = 'block';
    mobileSim.classList.remove('active');
    btnWeb.classList.add('active');
    btnMobile.classList.remove('active');
  } else {
    webDash.style.display = 'none';
    mobileSim.classList.add('active');
    btnWeb.classList.remove('active');
    btnMobile.classList.add('active');
  }
}

// Chart.js Waveform Initialization
function initWaveformChart() {
  const ctx = document.getElementById('waveformChart').getContext('2d');
  
  const initialData = generateSineData('Normal');

  waveformChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: initialData.labels,
      datasets: [{
        label: 'Voltage (pu)',
        data: initialData.values,
        borderColor: '#00f2fe',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4,
        fill: true,
        backgroundColor: (context) => {
          const chart = context.chart;
          const {ctx, chartArea} = chart;
          if (!chartArea) return null;
          const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
          gradient.addColorStop(0, 'rgba(0, 242, 254, 0.2)');
          gradient.addColorStop(1, 'rgba(0, 242, 254, 0.0)');
          return gradient;
        }
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: {
          min: -2.0,
          max: 2.0,
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b' }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

// Sine Wave Generator for Real-Time Canvas Visualization
function generateSineData(type) {
  const points = 100;
  const labels = [];
  const values = [];
  
  for (let i = 0; i < points; i++) {
    labels.push(i);
    let t = i / points * (4 * Math.PI); // 2 cycles
    let val = Math.sin(t);

    if (type === 'Sag') {
      val *= 0.5;
    } else if (type === 'Swell') {
      val *= 1.5;
    } else if (type === 'Interruption') {
      val *= 0.05;
    } else if (type === 'Harmonics') {
      val += 0.25 * Math.sin(3 * t) + 0.15 * Math.sin(5 * t);
    } else if (type === 'Transient') {
      if (i > 40 && i < 60) {
        val += 0.8 * Math.sin(15 * t) * Math.exp(-Math.pow(i - 50, 2) / 20);
      }
    }

    // Add tiny random measurement noise
    val += (Math.random() - 0.5) * 0.03;
    values.push(val);
  }

  return { labels, values };
}

// Live Animation Loop
let phaseShift = 0;
function startWaveformAnimation() {
  setInterval(() => {
    phaseShift += 0.15;
    const points = 100;
    const newValues = [];
    
    for (let i = 0; i < points; i++) {
      let t = (i / points * (4 * Math.PI)) + phaseShift;
      let val = Math.sin(t);

      if (currentDisturbance === 'Sag') val *= 0.5;
      else if (currentDisturbance === 'Swell') val *= 1.4;
      else if (currentDisturbance === 'Interruption') val *= 0.05;
      else if (currentDisturbance === 'Harmonics') val += 0.25 * Math.sin(3 * t);

      val += (Math.random() - 0.5) * 0.02;
      newValues.push(val);
    }

    waveformChart.data.datasets[0].data = newValues;
    waveformChart.data.datasets[0].borderColor = STATUS_COLORS[currentDisturbance] || '#00f2fe';
    waveformChart.update();
  }, 50);
}

// Dynamic Disturbance Simulation Trigger
function triggerSimulatedDisturbance() {
  const disturbanceTypes = ['Sag', 'Swell', 'Harmonics', 'Transient', 'Interruption', 'Normal'];
  const nextType = disturbanceTypes[Math.floor(Math.random() * disturbanceTypes.length)];
  
  currentDisturbance = nextType;

  // Compute metrics for event
  let rms = 0.998;
  let thd = 0.82;
  let conf = (0.92 + Math.random() * 0.07).toFixed(3);
  let dur = '0.0 ms';

  if (nextType === 'Sag') { rms = 0.624; thd = 1.15; dur = '45.0 ms'; }
  else if (nextType === 'Swell') { rms = 1.482; thd = 1.85; dur = '60.0 ms'; }
  else if (nextType === 'Interruption') { rms = 0.042; thd = 8.50; dur = '120.0 ms'; }
  else if (nextType === 'Harmonics') { rms = 1.050; thd = 14.80; dur = 'Continuous'; }
  else if (nextType === 'Transient') { rms = 1.120; thd = 4.20; dur = '5.0 ms'; }

  // Update UI Elements
  const stateColor = STATUS_COLORS[nextType] || '#10b981';
  document.getElementById('val-current-state').textContent = nextType;
  document.getElementById('val-current-state').style.color = stateColor;
  document.getElementById('val-rms').textContent = rms.toFixed(3);
  document.getElementById('val-thd').textContent = thd.toFixed(2);

  // Mobile View Updates
  document.getElementById('mobile-hero-status').textContent = nextType;
  document.getElementById('mobile-hero-status').style.color = stateColor;
  document.getElementById('mobile-hero-conf').textContent = (conf * 100).toFixed(1) + '%';
  document.getElementById('mobile-rms').textContent = rms.toFixed(3) + ' pu';
  document.getElementById('mobile-thd').textContent = thd.toFixed(2) + ' %';

  // Add event to history stream
  const newEvent = {
    time: new Date().toLocaleTimeString(),
    true_state: nextType,
    pred_class: nextType,
    confidence: (conf * 100).toFixed(1) + '%',
    rms: rms.toFixed(3),
    thd: thd.toFixed(2) + '%',
    duration: dur
  };

  eventHistory.unshift(newEvent);
  renderEventTables();
}

// Render Initial Events History
function seedInitialEvents() {
  eventHistory = [
    { time: '10:14:02', true_state: 'Normal', pred_class: 'Normal', confidence: '96.3%', rms: '0.998', thd: '0.82%', duration: '0.0 ms' },
    { time: '10:13:58', true_state: 'Sag', pred_class: 'Sag', confidence: '94.2%', rms: '0.624', thd: '1.15%', duration: '45.0 ms' },
    { time: '10:13:45', true_state: 'Harmonics', pred_class: 'Harmonics', confidence: '91.8%', rms: '1.050', thd: '14.8%', duration: 'Continuous' },
    { time: '10:13:20', true_state: 'Swell', pred_class: 'Swell', confidence: '95.1%', rms: '1.482', thd: '1.85%', duration: '60.0 ms' }
  ];
  renderEventTables();
}

function renderEventTables() {
  const tbody = document.getElementById('event-stream-tbody');
  const mobileList = document.getElementById('mobile-event-list');
  
  if (!tbody || !mobileList) return;

  tbody.innerHTML = '';
  mobileList.innerHTML = '';

  eventHistory.forEach(ev => {
    const color = STATUS_COLORS[ev.pred_class] || '#10b981';
    
    // Web Table Row
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${ev.time}</td>
      <td>${ev.true_state}</td>
      <td><span class="card-badge" style="background: rgba(255,255,255,0.05); color: ${color};">${ev.pred_class}</span></td>
      <td>${ev.confidence}</td>
      <td>${ev.rms}</td>
      <td>${ev.thd}</td>
      <td>${ev.duration}</td>
    `;
    tbody.appendChild(tr);

    // Mobile App Event Card
    const mobileCard = document.createElement('div');
    mobileCard.className = 'card';
    mobileCard.style.padding = '0.85rem';
    mobileCard.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span class="card-badge" style="background: rgba(255,255,255,0.05); color: ${color}; font-size: 0.8rem;">${ev.pred_class}</span>
        <span style="font-size: 0.75rem; color: var(--text-dim);">${ev.time}</span>
      </div>
      <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.4rem;">RMS: ${ev.rms} pu | THD: ${ev.thd}</div>
    `;
    mobileList.appendChild(mobileCard);
  });
}
