// Preload — exposes safe IPC bridge to renderer
const { contextBridge, ipcRenderer } = require('electron');

// Already using nodeIntegration: true so this is just for safety
// If you switch to contextIsolation: true, expose APIs here:
// contextBridge.exposeInMainWorld('electronAPI', { ... });