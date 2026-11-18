// Headless browser check of the revision 11 page: Figure 1 plays through the five-year windows, a click on the map
// stops it, a click on a year in panel b moves the map to the window ending that year, a click on the slider while
// playing stops it on the window clicked, and the console stays clean. Exits 1 on an error, a console error or
// exception, or any check that is false.
// Usage: node browser_check.mjs <browser executable> <page file> <output folder>
// Writes fig1-playing.png, fig1-clicked.png, infographic.png and browser-check.json to the output folder.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [browser, pageFile, outDir] = process.argv.slice(2);
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), 'r11-edge-'));
const proc = spawn(browser, ['--headless=new', '--disable-gpu', '--hide-scrollbars', `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`, '--window-size=1000,1400', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find(t => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(250);
  }
  throw new Error('browser did not start');
}

const result = { console: [], exceptions: [], checks: {} };
let ws, seq = 0;
const pending = new Map();
function send(method, params = {}) {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((ok, fail) => pending.set(id, { ok, fail }));
}
async function evaluate(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error('evaluate failed: ' + JSON.stringify(r.exceptionDetails).slice(0, 400));
  return r.result.value;
}
async function shot(name, selector) {
  const box = await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'start'});
    const r=e.getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,w:r.width,h:r.height};})()`);
  await sleep(400);
  const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: box.x, y: box.y, width: box.w, height: Math.min(box.h, 1400), scale: 1 } });
  writeFileSync(join(outDir, name), Buffer.from(r.data, 'base64'));
}
async function click(x, y) {
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
    await send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 });
}
const frame = () => evaluate(`document.querySelector('.map-ctl output').textContent`);

try {
  ws = new WebSocket(await target());
  await new Promise((ok, fail) => { ws.onopen = ok; ws.onerror = fail; });
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.fail(new Error(m.error.message)) : p.ok(m.result); }
    if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning', 'assert'].includes(m.params.type))
      result.console.push(m.params.type + ': ' + m.params.args.map(a => a.value ?? a.description).join(' '));
    if (m.method === 'Runtime.exceptionThrown') result.exceptions.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') result.console.push('log: ' + m.params.entry.text);
  };
  await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
  await send('Page.navigate', { url: pathToFileURL(resolve(pageFile)).href });
  for (let i = 0; i < 80 && !(await evaluate(`!!document.querySelector('.map-ctl')`)); i++) await sleep(250);
  result.checks.plotly_loaded = await evaluate(`typeof Plotly!=='undefined'`);
  result.checks.controls = await evaluate(`!!document.querySelector('.map-ctl')`);
  result.checks.charts_drawn = await evaluate(`[...document.querySelectorAll('.viz')].filter(d=>d.data).map(d=>d.id)`);
  await shot('infographic.png', '#infographic');
  await evaluate(`document.getElementById('fig1').scrollIntoView({block:'start'})`);
  const start = await frame();
  await sleep(4200);
  const playing = await frame();
  result.checks.frames_while_playing = [start, playing];
  result.checks.animates_until_click = start !== playing;
  await shot('fig1-playing.png', '#fig1');
  // click the middle of the map plot area: playing stops
  const map = await evaluate(`(()=>{const e=document.querySelector('#fig-map .nsewdrag');const r=e.getBoundingClientRect();return {x:r.left+r.width*.7,y:r.top+r.height*.8};})()`);
  await click(map.x, map.y);
  const stopped = await frame();
  await sleep(3000);
  result.checks.stops_on_map_click = stopped === (await frame());
  result.checks.button_after_click = await evaluate(`document.querySelector('.map-ctl button').textContent`);
  // click the 2015 dot of the shallow band in panel b: the map moves to 2011 to 2015
  const dot = await evaluate(`(()=>{const el=document.getElementById('fig-map-trend');const fl=el._fullLayout;const xa=fl.xaxis,ya=fl.yaxis;
    const tr=el.data.find(t=>t.mode==='markers');const i=tr.x.indexOf(2015);const r=el.querySelector('.nsewdrag').getBoundingClientRect();
    return {x:r.left+xa.l2p(2015),y:r.top+ya.l2p(tr.y[i])};})()`);
  await click(dot.x, dot.y);
  await sleep(800);
  const chosen = await frame();
  result.checks.panel_b_click_frame = chosen;
  result.checks.panel_b_click_moves_map = chosen.startsWith('2011 to 2015');
  result.checks.shade_on_panel_b = await evaluate(`(()=>{const s=document.getElementById('fig-map-trend').layout.shapes||[];return s.map(x=>[x.x0,x.x1]);})()`);
  await sleep(2600);
  result.checks.stays_after_panel_b_click = (await frame()) === chosen;
  await shot('fig1-clicked.png', '#fig1');
  // press Play, then click the slider a quarter of the way along: playing stops on the window under the click
  await evaluate(`document.querySelector('.map-ctl button').click()`);
  await sleep(1500);
  result.checks.playing_again = (await evaluate(`document.querySelector('.map-ctl button').textContent`)) === 'Pause';
  const bar = await evaluate(`(()=>{const e=document.querySelector('.map-ctl input[type=range]');e.scrollIntoView({block:'center'});
    const r=e.getBoundingClientRect();return {x:r.left+r.width*.25,y:r.top+r.height/2};})()`);
  await click(bar.x, bar.y);
  await sleep(300);
  const value = Number(await evaluate(`document.querySelector('.map-ctl input[type=range]').value`));
  const sliderFrame = await frame();
  result.checks.slider_click_value = value;
  result.checks.slider_click_frame = sliderFrame;
  result.checks.slider_click_moves_map = value > 0 && value < 8 && sliderFrame.startsWith(`${2005 + value} to ${2009 + value}`);
  await sleep(2600);
  result.checks.slider_click_stops = (await frame()) === sliderFrame &&
    (await evaluate(`document.querySelector('.map-ctl button').textContent`)) === 'Play';
} catch (error) {
  result.error = String(error && error.stack || error);
} finally {
  result.failed_checks = Object.entries(result.checks).filter(([, v]) => v === false).map(([k]) => k);
  writeFileSync(join(outDir, 'browser-check.json'), JSON.stringify(result, null, 2) + '\n');
  try { ws && ws.close(); } catch { }
  proc.kill();
  await sleep(800);
  try { rmSync(profile, { recursive: true, force: true }); } catch { }
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.error || result.exceptions.length || result.console.length || result.failed_checks.length ? 1 : 0);
}
