/* โหลดไฟล์ JSON ของร้านยา ใช้ร่วมกันทั้ง drug_dashboard (dashboard01) และ dashboard02
 *
 * PharmaData.load(base, files) -> Promise<{ key: json }>
 *   base  : โฟลเดอร์ที่เก็บ JSON เช่น '../dashboard02/'
 *   files : { drugs: 'drugs.json', stock: 'stock.json', log: 'dispense-log.json', issues: 'data-issues.json?' }
 *           ชื่อไฟล์ที่ลงท้ายด้วย ? คือไม่บังคับ (ถ้าไม่มีจะได้ null)
 *
 * วิธีโหลด
 * 1) fetch จากเซิร์ฟเวอร์ (python -m http.server หรือ Live Server)
 * 2) ถ้า fetch ไม่ได้ (เช่น เปิดไฟล์ตรงจาก file:// ) จะแสดงหน้าให้เลือกหรือลากไฟล์ JSON มาวาง
 *    แล้วแยกชนิดไฟล์จากโครงสร้างข้อมูล ชื่อไฟล์จึงไม่ต้องตรงเป๊ะ
 */
(function () {
  'use strict';

  const KIND_TEST = {
    drugs: (d) => has(d, 'generic_name'),
    stock: (d) => has(d, 'stock_id'),
    log: (d) => has(d, 'dispense_id'),
    issues: (d) => has(d, 'action') && has(d, 'file'),
  };
  const KIND_LABEL = {
    drugs: 'บัญชียา', stock: 'สต็อกรายล็อต', log: 'บันทึกการจ่ายยา', issues: 'บันทึกการคลีนข้อมูล',
  };

  function has(doc, key) {
    return !!(doc && Array.isArray(doc.items) && doc.items.length && key in doc.items[0]);
  }

  function parseSpec(files) {
    return Object.entries(files).map(([key, name]) => ({
      key, name: name.replace(/\?$/, ''), optional: name.endsWith('?'),
    }));
  }

  async function viaFetch(base, spec) {
    const out = {};
    await Promise.all(spec.map(async (f) => {
      let res;
      try {
        res = await fetch(base + f.name, { cache: 'no-store' });
      } catch (e) {
        if (f.optional) { out[f.key] = null; return; }
        throw e;
      }
      if (!res.ok) {
        if (f.optional) { out[f.key] = null; return; }
        throw new Error(`${f.name}: HTTP ${res.status}`);
      }
      out[f.key] = await res.json();
    }));
    return out;
  }

  function viaPicker(base, spec, reason) {
    return new Promise((resolve) => {
      const got = {};
      const box = document.createElement('div');
      box.setAttribute('role', 'dialog');
      box.setAttribute('aria-modal', 'true');
      box.setAttribute('aria-labelledby', 'pd-title');
      box.style.cssText = 'position:fixed;inset:0;z-index:100;display:grid;place-items:center;padding:16px;'
        + 'background:var(--surface-dark,#1a2129);color:var(--on-dark,#fff);font-family:inherit';
      box.innerHTML = `
        <div style="max-width:620px;width:100%">
          <h2 id="pd-title" style="font-size:28px;margin:0 0 8px;font-weight:700">เลือกไฟล์ข้อมูล</h2>
          <p style="margin:0 0 20px;font-weight:300;color:var(--on-dark-soft,#bbb);line-height:1.6">
            เบราว์เซอร์ไม่ยอมให้หน้าเว็บอ่านไฟล์ JSON เองเมื่อเปิดไฟล์ HTML ตรง ๆ
            ลากไฟล์ JSON จาก${base === './' ? 'โฟลเดอร์เดียวกับหน้านี้' : `โฟลเดอร์ <code>${base}</code>`} มาวาง หรือกดปุ่มเลือกไฟล์ (เลือกหลายไฟล์พร้อมกันได้)</p>
          <label id="pd-drop" style="display:block;border:2px dashed rgba(255,255,255,.35);padding:28px;text-align:center;cursor:pointer">
            <input id="pd-input" type="file" accept=".json,application/json" multiple style="position:absolute;opacity:0;width:1px;height:1px">
            <span style="display:inline-block;background:var(--primary,#1c69d4);color:#fff;font-weight:700;padding:14px 28px">เลือกไฟล์ JSON</span>
            <span style="display:block;margin-top:10px;font-weight:300;color:var(--on-dark-soft,#bbb)">หรือลากไฟล์มาวางตรงนี้</span>
          </label>
          <ul id="pd-list" style="list-style:none;padding:0;margin:20px 0 0;display:grid;gap:8px"></ul>
          <p id="pd-msg" style="min-height:1.5em;margin:12px 0 0;color:#fab219"></p>
          <details style="margin-top:20px;font-weight:300;color:var(--on-dark-soft,#bbb)">
            <summary style="cursor:pointer">ไม่อยากเลือกไฟล์ทุกครั้ง?</summary>
            <p style="line-height:1.6">หน้านี้หาไฟล์ <code>data.js</code> ไม่เจอ ให้รัน
            <code style="background:rgba(255,255,255,.1);padding:2px 6px">python build_data_js.py</code>
            ในโฟลเดอร์ <b>dashboard02</b> แล้วเปิดหน้านี้ใหม่ จะขึ้น dashboard ทันที</p>
            <p style="line-height:1.6">หรือเปิดผ่าน local server แทน: ในโฟลเดอร์ <b>AILern</b> พิมพ์
            <code style="background:rgba(255,255,255,.1);padding:2px 6px">python -m http.server</code>
            แล้วเปิด <code>http://localhost:8000/</code> ตามด้วยชื่อโฟลเดอร์ dashboard
            (หรือใช้ Live Server ใน VS Code)</p>
            <p style="font-size:13px">สาเหตุที่โหลดเองไม่ได้: ${String(reason && reason.message || reason).replace(/</g, '&lt;')}</p>
          </details>
        </div>`;
      document.body.appendChild(box);
      const list = box.querySelector('#pd-list');
      const msg = box.querySelector('#pd-msg');

      function paint() {
        list.innerHTML = spec.map((f) => {
          const ok = got[f.key] !== undefined;
          return `<li style="display:flex;gap:10px;align-items:center">
            <span style="width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:13px;
              background:${ok ? '#0ca30c' : 'transparent'};border:1px solid ${ok ? '#0ca30c' : 'rgba(255,255,255,.4)'}">${ok ? '✓' : ''}</span>
            <span>${KIND_LABEL[f.key] || f.key} <span style="color:var(--on-dark-soft,#bbb);font-weight:300">(${f.name}${f.optional ? ' · ไม่บังคับ' : ''})</span></span></li>`;
        }).join('');
        const missing = spec.filter((f) => !f.optional && got[f.key] === undefined);
        if (!missing.length) {
          spec.forEach((f) => { if (got[f.key] === undefined) got[f.key] = null; });
          box.remove();
          resolve(got);
        }
      }

      async function take(fileList) {
        msg.textContent = '';
        for (const file of fileList) {
          try {
            const doc = JSON.parse(await file.text());
            const kind = spec.find((f) => KIND_TEST[f.key] && KIND_TEST[f.key](doc));
            if (kind) got[kind.key] = doc;
            else msg.textContent = `ไม่รู้จักไฟล์ ${file.name}`;
          } catch (e) {
            msg.textContent = `อ่านไฟล์ ${file.name} ไม่ได้: ไม่ใช่ JSON ที่ถูกต้อง`;
          }
        }
        paint();
      }

      box.querySelector('#pd-input').addEventListener('change', (e) => take(e.target.files));
      const drop = box.querySelector('#pd-drop');
      drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.style.borderColor = '#fff'; });
      drop.addEventListener('dragleave', () => { drop.style.borderColor = 'rgba(255,255,255,.35)'; });
      drop.addEventListener('drop', (e) => {
        e.preventDefault();
        drop.style.borderColor = 'rgba(255,255,255,.35)';
        take(e.dataTransfer.files);
      });
      paint();
    });
  }

  // ข้อมูลจาก data.js (สร้างโดย build_data_js.py) ใช้ตอนเปิดไฟล์ตรงจาก file://
  function viaBundle(spec) {
    const bundle = window.PHARMA_JSON;
    if (!bundle) return null;
    const out = {};
    for (const f of spec) {
      if (bundle[f.name]) out[f.key] = bundle[f.name];
      else if (f.optional) out[f.key] = null;
      else return null;
    }
    return out;
  }

  async function load(base, files) {
    const spec = parseSpec(files);
    // เปิดจากไฟล์: ใช้ data.js เลย ไม่ต้องลอง fetch ที่เบราว์เซอร์ไม่ยอมอยู่แล้ว
    if (location.protocol === 'file:') {
      const b = viaBundle(spec);
      if (b) return b;
    }
    // เปิดผ่านเซิร์ฟเวอร์: อ่านไฟล์ JSON ตัวจริง (ได้ข้อมูลล่าสุดเสมอ)
    try {
      return await viaFetch(base, spec);
    } catch (err) {
      return viaBundle(spec) || viaPicker(base, spec, err);
    }
  }

  window.PharmaData = { load };
})();
