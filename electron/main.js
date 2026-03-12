const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const WebSocket = require('ws');

app.commandLine.appendSwitch('disable-background-networking');
app.commandLine.appendSwitch('disable-component-update');
app.commandLine.appendSwitch('disable-domain-reliability');
app.commandLine.appendSwitch('disable-logging');
app.commandLine.appendSwitch('log-level', '3');
app.commandLine.appendSwitch(
  'disable-features',
  [
    'AutofillServerCommunication',
    'CertificateTransparencyComponentUpdater',
    'MediaRouter',
    'OptimizationHints'
  ].join(',')
);

let hudWindow;
let ws;
let reconnectTimer;

function createHUD() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  hudWindow = new BrowserWindow({
    width: 320,
    height: 195,
    x: width - 340,
    y: height - 215,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  hudWindow.loadFile('index.html');
  hudWindow.setIgnoreMouseEvents(false);

  // Keep always on top across all workspaces
  hudWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  hudWindow.setAlwaysOnTop(true, 'screen-saver');
}

// ── WebSocket connection to Python backend ────────────────────────────────────
function connectToPython() {
  ws = new WebSocket('ws://localhost:8765');

  ws.on('open', () => {
    console.log('[Electron] Connected to Python backend');
    hudWindow?.webContents.send('connection-status', { connected: true });
  });

  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data);
      // Forward all backend events to the renderer
      hudWindow?.webContents.send('pipeline-event', msg);
    } catch (e) {
      console.error('[Electron] Bad message from Python:', e);
    }
  });

  ws.on('close', () => {
    console.log('[Electron] Python backend disconnected — retrying in 2s...');
    hudWindow?.webContents.send('connection-status', { connected: false });
    reconnectTimer = setTimeout(connectToPython, 2000);
  });

  ws.on('error', () => {
    ws.terminate();
  });
}

// ── IPC from renderer → Python ────────────────────────────────────────────────
ipcMain.on('send-to-python', (event, msg) => {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
});

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createHUD();
  connectToPython();
});

app.on('window-all-closed', () => {
  clearTimeout(reconnectTimer);
  ws?.close();
  app.quit();
});