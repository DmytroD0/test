const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('widget', {
  getSettings: () => ipcRenderer.invoke('get-settings'),
  setHeight: h => ipcRenderer.send('set-height', h),
  setAlwaysOnTop: v => ipcRenderer.send('set-always-on-top', v),
  setAutoStart: v => ipcRenderer.send('set-auto-start', v),
  quit: () => ipcRenderer.send('quit'),
});
