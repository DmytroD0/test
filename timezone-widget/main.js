const { app, BrowserWindow, ipcMain, screen } = require('electron');
const fs = require('fs');
const path = require('path');

const statePath = () => path.join(app.getPath('userData'), 'window-state.json');

function loadState() {
  try { return JSON.parse(fs.readFileSync(statePath(), 'utf8')); } catch { return {}; }
}
function saveState(patch) {
  const s = { ...loadState(), ...patch };
  try { fs.writeFileSync(statePath(), JSON.stringify(s)); } catch {}
  return s;
}

// Тільки один екземпляр віджета
if (!app.requestSingleInstanceLock()) app.quit();

let win;
function create() {
  const state = loadState();
  const { workArea } = screen.getPrimaryDisplay();
  const width = 320;
  let x = state.x ?? workArea.x + workArea.width - width - 24;
  let y = state.y ?? workArea.y + 24;
  // якщо збережена позиція поза екранами — повертаємо у видиму зону
  const visible = screen.getAllDisplays().some(d =>
    x >= d.workArea.x - 50 && x < d.workArea.x + d.workArea.width - 50 &&
    y >= d.workArea.y - 10 && y < d.workArea.y + d.workArea.height - 50);
  if (!visible) { x = workArea.x + workArea.width - width - 24; y = workArea.y + 24; }

  win = new BrowserWindow({
    width, height: 400, x, y,
    frame: false,
    transparent: true,
    resizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    hasShadow: false,
    alwaysOnTop: !!state.alwaysOnTop,
    webPreferences: { preload: path.join(__dirname, 'preload.js') },
  });
  win.loadFile(path.join(__dirname, 'index.html'));

  win.on('moved', () => {
    const [nx, ny] = win.getPosition();
    saveState({ x: nx, y: ny });
  });
}

ipcMain.handle('get-settings', () => {
  const s = loadState();
  return {
    alwaysOnTop: !!s.alwaysOnTop,
    autoStart: app.getLoginItemSettings().openAtLogin,
  };
});
ipcMain.on('set-height', (_e, h) => {
  if (!win) return;
  const [w] = win.getSize();
  win.setSize(w, Math.max(80, Math.min(1000, Math.round(h))));
});
ipcMain.on('set-always-on-top', (_e, v) => {
  saveState({ alwaysOnTop: !!v });
  win?.setAlwaysOnTop(!!v);
});
ipcMain.on('set-auto-start', (_e, v) => {
  app.setLoginItemSettings({ openAtLogin: !!v });
});
ipcMain.on('quit', () => app.quit());

app.on('second-instance', () => { win?.show(); win?.focus(); });
app.whenReady().then(create);
app.on('window-all-closed', () => app.quit());
