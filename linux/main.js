const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs   = require('fs');

let mainWindow;
let pendingFilePath = null;

// Handle file passed as command-line argument (file-association open)
const filePath = process.argv.find(arg =>
    /\.(zip|jar|apk|docx|xlsx|pptx|epub)$/i.test(arg)
);
if (filePath) pendingFilePath = path.resolve(filePath);

// Single-instance lock — route second launch to existing window
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
    app.quit();
} else {
    app.on('second-instance', (event, argv) => {
        const file = argv.find(arg => /\.(zip|jar|apk|docx|xlsx|pptx|epub)$/i.test(arg));
        if (file && mainWindow) loadFileIntoApp(path.resolve(file));
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.focus();
        }
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1060,
        height: 760,
        minWidth: 560,
        minHeight: 460,
        backgroundColor: '#121212',
        title: 'Immortal Unzip',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        },
        show: false
    });

    mainWindow.setMenuBarVisibility(false);
    mainWindow.loadFile('immortal-unzip.html');

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        if (pendingFilePath) {
            setTimeout(() => loadFileIntoApp(pendingFilePath), 500);
            pendingFilePath = null;
        }
    });

    mainWindow.on('closed', () => { mainWindow = null; });
}

function loadFileIntoApp(filePath) {
    if (!mainWindow || !fs.existsSync(filePath)) return;
    try {
        const data     = fs.readFileSync(filePath);
        const base64   = data.toString('base64');
        const fileName = path.basename(filePath);
        mainWindow.webContents.executeJavaScript(
            `loadFileFromWindows(${JSON.stringify(fileName)}, ${JSON.stringify(base64)});`
        );
    } catch (err) {
        console.error('Failed to load file:', err);
    }
}

// ── IPC Handlers ──────────────────────────────────────────────────────────────

ipcMain.handle('pick-file', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Open ZIP file',
        filters: [
            { name: 'ZIP Archives', extensions: ['zip', 'jar', 'apk', 'docx', 'xlsx', 'pptx', 'epub'] },
            { name: 'All Files',    extensions: ['*'] }
        ],
        properties: ['openFile']
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    const fp   = result.filePaths[0];
    const data = fs.readFileSync(fp);
    return { fileName: path.basename(fp), data: data.toString('base64') };
});

ipcMain.handle('save-file', async (event, { fileName, data }) => {
    const ext = path.extname(fileName).slice(1).toLowerCase() || 'bin';
    const result = await dialog.showSaveDialog(mainWindow, {
        title: 'Save extracted file',
        defaultPath: fileName,
        filters: [
            { name: ext.toUpperCase() + ' File', extensions: [ext] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });
    if (result.canceled || !result.filePath) return false;
    fs.writeFileSync(result.filePath, Buffer.from(data, 'base64'));
    return true;
});

// macOS open-file event (also fired on Windows when using file associations)
app.on('open-file', (event, filePath) => {
    event.preventDefault();
    if (mainWindow) loadFileIntoApp(filePath);
    else pendingFilePath = filePath;
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => { app.quit(); });

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
