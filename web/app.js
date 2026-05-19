/* Immortal-Zip — browser implementation.
 *
 * Zip / unzip: JSZip handles standard archives reliably.
 * Repair: own scanner that walks the file bytes looking for Local File
 * Header signatures (PK\x03\x04). For each entry we decompress the payload
 * via fflate (raw DEFLATE) and write a fresh archive — independent of the
 * original Central Directory, so we tolerate truncation and EOCD damage.
 */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  const status = $('#status');
  const progress = $('#progress');

  function setStatus(msg) { status.textContent = msg; }
  function setProgress(pct) { progress.value = Math.max(0, Math.min(100, pct | 0)); }

  // --- Tabs ---------------------------------------------------------------
  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      $('#tab-' + btn.dataset.tab).classList.add('active');
    });
  });

  // --- Dropzone helper ----------------------------------------------------
  function wireDropzone(labelSel, inputSel, onFiles) {
    const label = $(labelSel);
    const input = $(inputSel);
    label.addEventListener('dragover', (e) => { e.preventDefault(); label.classList.add('drag'); });
    label.addEventListener('dragleave', () => label.classList.remove('drag'));
    label.addEventListener('drop', (e) => {
      e.preventDefault();
      label.classList.remove('drag');
      if (e.dataTransfer && e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
    });
    input.addEventListener('change', () => { if (input.files.length) onFiles(input.files); });
  }

  // --- Zip ----------------------------------------------------------------
  let zipFiles = [];
  wireDropzone('label[for=zipInput]', '#zipInput', (files) => {
    zipFiles = zipFiles.concat(Array.from(files));
    renderZipList();
  });

  function renderZipList() {
    const ul = $('#zipList');
    ul.innerHTML = '';
    zipFiles.forEach((f, i) => {
      const li = document.createElement('li');
      li.innerHTML = `<span>${escapeHtml(f.webkitRelativePath || f.name)}</span>
        <a href="#" data-i="${i}">remove</a>`;
      ul.appendChild(li);
    });
    ul.querySelectorAll('a').forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      zipFiles.splice(Number(a.dataset.i), 1);
      renderZipList();
    }));
  }

  $('#zipBtn').addEventListener('click', async () => {
    if (!zipFiles.length) { setStatus('Add at least one file.'); return; }
    setStatus('Building archive…');
    setProgress(0);
    const zip = new JSZip();
    zipFiles.forEach((f) => zip.file(f.webkitRelativePath || f.name, f));
    const blob = await zip.generateAsync(
      { type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } },
      (meta) => { setProgress(meta.percent); setStatus(`Compressing: ${meta.currentFile || ''}`); }
    );
    saveBlob(blob, $('#zipName').value || 'archive.zip');
    setStatus('Zip created.');
    setProgress(100);
  });

  // --- Unzip --------------------------------------------------------------
  let unzipFile = null;
  wireDropzone('label[for=unzipInput]', '#unzipInput', (files) => {
    unzipFile = files[0];
    $('#unzipName').textContent = unzipFile.name;
    $('#unzipBtn').disabled = false;
  });

  $('#unzipBtn').addEventListener('click', async () => {
    if (!unzipFile) return;
    setStatus('Reading archive…');
    setProgress(0);
    try {
      const zip = await JSZip.loadAsync(await unzipFile.arrayBuffer());
      const entries = Object.values(zip.files);
      const ul = $('#unzipResults');
      ul.innerHTML = '';
      let done = 0;
      for (const entry of entries) {
        if (entry.dir) { done++; continue; }
        const blob = await entry.async('blob');
        const url = URL.createObjectURL(blob);
        const li = document.createElement('li');
        li.innerHTML = `<span>${escapeHtml(entry.name)}</span>
          <a href="${url}" download="${escapeAttr(basename(entry.name))}">download</a>`;
        ul.appendChild(li);
        done++;
        setProgress((done / entries.length) * 100);
        setStatus(`Extracted: ${entry.name}`);
      }
      setStatus(`Extracted ${entries.length} entries.`);
    } catch (err) {
      setStatus('Could not open — try the Repair tab.');
      console.error(err);
    }
  });

  // --- Repair -------------------------------------------------------------
  let repairFile = null;
  wireDropzone('label[for=repairInput]', '#repairInput', (files) => {
    repairFile = files[0];
    $('#repairName').textContent = repairFile.name;
    $('#repairBtn').disabled = false;
  });

  $('#repairBtn').addEventListener('click', async () => {
    if (!repairFile) return;
    setStatus('Scanning for salvageable members…');
    setProgress(0);
    const log = $('#repairLog');
    log.textContent = '';

    const bytes = new Uint8Array(await repairFile.arrayBuffer());
    const entries = scanLocalHeaders(bytes);
    if (!entries.length) {
      setStatus('No zip data found.');
      log.textContent = 'No PK\\x03\\x04 signatures detected. File may not be a zip.';
      return;
    }

    const out = new JSZip();
    let recovered = 0;
    let skipped = 0;
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i];
      try {
        const payload = extractPayload(bytes, e, entries[i + 1]);
        if (e.name.endsWith('/')) {
          out.folder(e.name);
        } else {
          out.file(e.name, payload);
        }
        recovered++;
        log.textContent += `recovered  ${e.name}\n`;
      } catch (err) {
        skipped++;
        log.textContent += `skipped    ${e.name} (${err.message || err})\n`;
      }
      setProgress(((i + 1) / entries.length) * 100);
    }

    if (!recovered) {
      setStatus('Repair failed — no readable members.');
      return;
    }

    setStatus('Writing repaired archive…');
    const blob = await out.generateAsync({ type: 'blob', compression: 'DEFLATE' });
    const baseName = repairFile.name.replace(/\.zip$/i, '') + '.repaired.zip';
    saveBlob(blob, baseName);
    setStatus(`Recovered ${recovered}, skipped ${skipped}.`);
  });

  function scanLocalHeaders(bytes) {
    const sig = [0x50, 0x4b, 0x03, 0x04];
    const entries = [];
    const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let i = 0; i + 30 <= bytes.length; i++) {
      if (bytes[i] !== sig[0] || bytes[i + 1] !== sig[1] || bytes[i + 2] !== sig[2] || bytes[i + 3] !== sig[3]) continue;
      const flags = dv.getUint16(i + 6, true);
      const method = dv.getUint16(i + 8, true);
      const compSize = dv.getUint32(i + 18, true);
      const uncompSize = dv.getUint32(i + 22, true);
      const nameLen = dv.getUint16(i + 26, true);
      const extraLen = dv.getUint16(i + 28, true);
      const nameStart = i + 30;
      const dataStart = nameStart + nameLen + extraLen;
      if (dataStart > bytes.length) break;
      const rawName = bytes.subarray(nameStart, nameStart + nameLen);
      let name;
      try { name = new TextDecoder('utf-8', { fatal: false }).decode(rawName); }
      catch (_e) { name = String.fromCharCode.apply(null, rawName); }
      entries.push({ offset: i, dataStart, name, method, flags, compSize, uncompSize });
      i = dataStart + (compSize > 0 ? compSize : 0) - 1;
    }
    return entries;
  }

  function extractPayload(bytes, entry, next) {
    let end;
    if (entry.compSize > 0) {
      end = entry.dataStart + entry.compSize;
    } else if (next) {
      end = next.offset;
    } else {
      end = findNextHeader(bytes, entry.dataStart);
    }
    const slice = bytes.subarray(entry.dataStart, end);
    if (entry.method === 0) return slice;
    if (entry.method === 8) {
      return fflate.inflateSync(slice);
    }
    throw new Error('unsupported method ' + entry.method);
  }

  function findNextHeader(bytes, from) {
    const sigs = [
      [0x50, 0x4b, 0x03, 0x04],
      [0x50, 0x4b, 0x01, 0x02],
      [0x50, 0x4b, 0x05, 0x06],
      [0x50, 0x4b, 0x07, 0x08],
    ];
    for (let i = from; i + 4 <= bytes.length; i++) {
      for (const s of sigs) {
        if (bytes[i] === s[0] && bytes[i + 1] === s[1] && bytes[i + 2] === s[2] && bytes[i + 3] === s[3]) return i;
      }
    }
    return bytes.length;
  }

  // --- Utilities ----------------------------------------------------------
  function saveBlob(blob, name) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function basename(p) { return p.replace(/^.*[\\/]/, ''); }
  function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function escapeAttr(s) { return escapeHtml(s); }

  // --- PWA install prompt -------------------------------------------------
  let deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    $('#installBtn').hidden = false;
  });
  $('#installBtn').addEventListener('click', async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    $('#installBtn').hidden = true;
  });
})();
