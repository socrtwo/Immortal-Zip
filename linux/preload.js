const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    pickFile: ()                   => ipcRenderer.invoke('pick-file'),
    saveFile: (fileName, data)     => ipcRenderer.invoke('save-file', { fileName, data }),
    isElectron: true
});
