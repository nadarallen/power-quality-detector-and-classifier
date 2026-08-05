# PQD Classifier — Mobile Application Scaffolding

This directory contains the production-grade **React Native / Expo** cross-platform mobile app scaffolding for iOS and Android.

---

## 📱 Mobile Architecture & Component Tree

```
mobile_app/
├── package.json                   # Mobile App dependencies (React Native, Expo, Firebase)
├── app.json                       # Expo app config (slug, package ID, assets)
├── App.js                         # Root App entry point
└── src/
    ├── theme/
    │   └── minimalismTheme.js     # Minimalism UI design system tokens
    ├── config/
    │   └── firebase.js            # Mobile Firebase Firestore SDK initialization
    ├── components/
    │   ├── StatusHeroCard.js      # Main Disturbance Status Card
    │   ├── MetricGrid.js          # RMS Voltage & THD % metric cards
    │   └── EventCard.js           # Minimalist historical disturbance list item
    └── screens/
        └── LiveMonitoringScreen.js# Primary real-time grid monitoring screen
```

---

## 🎨 Minimalism UI Design Tokens (`src/theme/minimalismTheme.js`)

- **Canvas**: `#080B11` (Deep Space Carbon)
- **Container Surfaces**: `#121826` (Solid Obsidian) with `1px` subtle border `rgba(255, 255, 255, 0.08)`
- **Accent Glow**: `#00F2FE` (Cyan) / `#4FACFE` (Neon Sky)
- **Color-Coded Badges**:
  - `Normal`: `#10B981` (Emerald Green)
  - `Sag`: `#F59E0B` (Amber)
  - `Swell`: `#EF4444` (Coral Red)
  - `Harmonics`: `#8B5CF6` (Purple)
  - `Interruption`: `#DC2626` (Crimson)

---

## 🚀 How to Run the Mobile App

### Prerequisites
Install Expo CLI globally or via npx:
```bash
npm install -g expo-cli
```

### Installation & Run Commands
1. Navigate to the `mobile_app` folder:
   ```bash
   cd mobile_app
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Expo development server:
   ```bash
   npx expo start
   ```

4. **Run on Mobile Device**:
   - Install **Expo Go** from the iOS App Store or Google Play Store.
   - Scan the QR code generated in your terminal to launch the mobile app live on your phone!
