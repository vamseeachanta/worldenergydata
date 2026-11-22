// Exercise the embedded controls without starting a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() { this.textContent = ''; this.value = ''; this.children = []; this.handlers = {}; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  replaceChildren() { this.children = []; }
  append(item) { this.children.push(item); }
  click() { this.clicked = true; }
}

(async () => {
  const html = fs.readFileSync(process.argv[2], {encoding: 'utf8'});
  const elements = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new Element()]));
  const get = id => { assert.ok(elements.has(id), `Missing control: ${id}`); return elements.get(id); };
  for (const id of ['calculation', 'change-data']) {
    get(id).textContent = html.match(new RegExp(`<script id="${id}" type="application/json">(.*?)</script>`, 's'))[1];
  }
  const points = [...html.matchAll(/data-tooltip="([^"]+)"/g)].map(match => {
    const point = new Element(); point.dataset = {tooltip: match[1]}; return point;
  });
  let saved = '';
  let blob;
  const context = {
    document: {getElementById: get, querySelectorAll: () => points, createElement: () => new Element()},
    window: {
      confirm: () => true,
      showSaveFilePicker: async options => {
        assert.equal(options.suggestedName, 'index.comments.json');
        return {createWritable: async () => ({write: async text => { saved = text; }, close: async () => {}})};
      },
    },
    URL: {createObjectURL: value => { blob = value; return 'blob:comments'; }, revokeObjectURL: () => {}},
    Blob,
    setTimeout: callback => callback(),
  };
  vm.runInNewContext(html.match(/<script>(.*?)<\/script>/s)[1], context);
  points[0].handlers.focus();
  assert.equal(get('chart-detail').textContent, points[0].dataset.tooltip);
  get('previous-revision').handlers.change({target: {value: 'A'}});
  assert.match(get('change-list').children[0].textContent, /No engineering changes/);
  get('previous-revision').handlers.change({target: {value: 'none'}});
  assert.equal(get('change-list').children.length, 2);
  get('comment-section').value = 'Worked example';
  get('comment-text').value = '<example text> with Unicode: ≤';
  get('comment-form').handlers.submit({preventDefault() {}});
  assert.equal(get('comment-list').children.length, 1);
  assert.equal(get('comment-list').children[0].textContent, 'Worked example: <example text> with Unicode: ≤');
  await get('save-comments').handlers.click();
  const parsed = JSON.parse(saved);
  assert.equal(parsed.comments[0].text, '<example text> with Unicode: ≤');
  assert.ok(saved.endsWith('\n'));
  // Invalid files preserve the displayed comments.
  await get('load-comments').handlers.change({target: {files: [{text: async () => '{}'}]}});
  assert.equal(get('comment-list').children.length, 1);
  assert.match(get('comment-status').textContent, /not loaded/);
  // Loading a valid file restores comments through textContent.
  parsed.comments[0].text = 'Restored';
  await get('load-comments').handlers.change({target: {files: [{text: async () => JSON.stringify(parsed)}]}});
  assert.equal(get('comment-list').children[0].textContent, 'Worked example: Restored');
  // A cancelled file picker leaves an explicit unsaved status.
  context.window.showSaveFilePicker = async () => { throw new Error('Cancelled'); };
  await get('save-comments').handlers.click();
  assert.match(get('comment-status').textContent, /remain unsaved/);
  // The fallback download is valid JSON too.
  delete context.window.showSaveFilePicker;
  await get('save-comments').handlers.click();
  assert.equal(JSON.parse(await blob.text()).comments[0].text, 'Restored');
  assert.match(get('comment-status').textContent, /download was requested/);
  console.log('Embedded chart, changes and comment controls passed.');
})().catch(error => { console.error(error.message); process.exitCode = 1; });
