// Targeted checks for the four issues in ACCEPTANCE-2026-10-29.md.
// Uses the shipped Vue reactivity and actual component setup functions; no database.
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const root = resolve(__dirname, '..');
const source = path => readFileSync(resolve(root, 'backend/static', path), 'utf8');

function load(token = '') {
  const storage = new Map(token ? [['lms_token', token]] : []);
  const mounted = [], messages = [];
  const context = vm.createContext({
    console, URLSearchParams, setTimeout, clearTimeout, setInterval, clearInterval,
    localStorage: {getItem: key => storage.get(key), setItem: (k,v) => storage.set(k,v), removeItem: k => storage.delete(k)},
    window: {innerWidth: 1200, location: {hash: '#dashboard'}, addEventListener() {}},
    ElementPlus: {ElMessage: {error: m => messages.push(m), warning: m => messages.push(m), success: m => messages.push(m)}, ElMessageBox: {}},
    HomeworkPanel: {}, CampusExamPanel: {}, CommunicationPanel: {}, CertificatePanel: {}, PlatformSettingsPage: {},
    fetch: async () => ({status: 200, ok: true, text: async () => '{}'}),
  });
  vm.runInContext(source('vendor/vue-3.5.13/vue.global.prod.js'), context);
  context.Vue.onMounted = fn => mounted.push(fn);
  context.Vue.onUnmounted = () => {};
  context.Vue.createApp = () => ({use() {}, component() {}, mount() {}, config: {globalProperties: {}}});
  vm.runInContext(source('js/api.js'), context);
  vm.runInContext(source('js/app.js'), context);
  return {run: code => vm.runInContext(code, context), mounted, messages, context};
}

test('ISSUE-01: DOCX passes the actual upload hook and file picker', () => {
  const env = load();
  assert.equal(env.run("MediaPage.setup().checkUpload({name:'lesson.DOCX'})"), true);
  assert.match(env.run('MediaPage.template'), /:accept="[^"\n]*\.docx/);
  assert.equal(env.run("MediaPage.setup().checkUpload({name:'legacy.doc'})"), false);
});

test('ISSUE-02: new chapters load video; refresh and type changes use the current type', async () => {
  const env = load();
  env.run("var queries=[]; api.listMedia=async q=>{queries.push(q.media_type);return {items:[{id:'video',name:'clip.mp4'}]}}; var page=CourseDetailPage.setup({id:'course'}); page.openAddCh();");
  await env.run('Vue.nextTick()');
  assert.equal(env.run('queries[0]'), 'video');
  assert.equal(env.run('page.mediaList.value[0].id'), 'video');
  // Compile the actual button expression, with a real event-shaped argument.
  const handler = env.run('CourseDetailPage.template').match(/@click="([^"]*loadMedia[^\"]*)"/)[1];
  env.context.page = env.run('page');
  env.context.event = {type: 'click'};
  await env.run(`(async()=>{with(page){const $event=event; ${handler === 'loadMedia' ? 'await loadMedia($event)' : `await (${handler})`};}})()`);
  assert.equal(env.run('queries.at(-1)'), 'video');
  env.run("page.chForm.content_type='document';page.onTypeChange();");
  await env.run('Vue.nextTick()');
  assert.equal(env.run('queries.at(-1)'), 'document');
  env.run("api.listMedia=async()=>{throw new Error('素材读取失败')};");
  await env.run("page.loadMedia('video')");
  assert.equal(env.messages.at(-1), '素材读取失败');
  assert.equal(env.run('page.mediaList.value.length'), 0);
});

test('ISSUE-03: first failed identity load invalidates the cached component immediately', async () => {
  const env = load('revoked-token');
  env.run("api.getUnreadCount=async()=>({count:0}); var page=App.setup();");
  assert.equal(env.run('page.currentComponent.value'), null);
  env.context.fetch = async () => ({status: 401, ok: false, text: async () => '{"detail":"会话失效"}'});
  await env.mounted.at(-1)();
  assert.equal(env.run('api.isLoggedIn()'), false);
  assert.equal(env.run('page.currentComponent.value===LoginPage'), true);
  env.run("api.setToken('replacement');page.userInfo.value={roles:[]};");
  assert.equal(env.run('page.currentComponent.value===DashboardPage'), true);
  env.run('api.clearToken()');
  assert.equal(env.run('page.currentComponent.value===LoginPage'), true);
});

test('CM-02: editing refresh uses its content type; chapter order is loaded and saved', async () => {
  const env = load();
  env.run("var queries=[],saved=[];api.listMedia=async q=>{queries.push(q.media_type);return {items:[]}};api.updateChapter=async(c,id,body)=>saved.push({...body});api.addChapter=async(c,body)=>saved.push({...body});api.getCourse=async()=>page.course.value; var page=CourseDetailPage.setup({id:'course'});page.course.value={can_manage:true,chapters:[{sort_order:10},{sort_order:30}]};page.openEditCh({id:'chapter',title:'课件',content_type:'document',sort_order:30,estimated_minutes:1,is_required:true});");
  await env.run('Vue.nextTick()');
  assert.equal(env.run('page.editChForm.sort_order'), 30);
  const template = env.run('CourseDetailPage.template');
  const dialog = template.slice(template.indexOf('v-model="showEditCh"'), template.indexOf('v-model="showExamConfig"'));
  const handler = dialog.match(/@click="([^"]*loadMedia[^\"]*)"/)[1];
  env.context.page = env.run('page');
  env.context.event = {type:'click'};
  await env.run(`(async()=>{with(page){const $event=event;${handler==='loadMedia'?'await loadMedia($event)':`await (${handler})`};}})()`);
  assert.equal(env.run('queries.at(-1)'), 'document');
  assert.match(dialog, /v-model="editChForm.sort_order"/);
  assert.match(template, /v-model="chForm.sort_order"/);
  env.run('page.editChForm.sort_order=5');
  await env.run('page.doEditCh()');
  assert.equal(env.run('saved[0].sort_order'), 5);
  env.run('page.openAddCh()');
  assert.equal(env.run('page.chForm.sort_order'), 31);
  env.run("page.chForm.title='新章节';page.chForm.content_type='text';page.chForm.sort_order=15");
  await env.run('page.doAddCh()');
  assert.equal(env.run('saved[1].sort_order'), 15);
});

test('ISSUE-04: validation arrays give Chinese field messages and preserve business errors', async () => {
  const env = load();
  for (const [detail, expected] of [
    [[{loc:['body','email'],type:'value_error',msg:'value is not a valid email address'}], '邮箱格式不正确'],
    [[{loc:['body','username'],type:'string_too_short',msg:'String too short'}], '用户名填写不正确，请检查后重试'],
    ['邮箱已被使用', '邮箱已被使用'],
  ]) {
    env.context.fetch = async () => ({status: 422, ok: false, text: async () => JSON.stringify({detail})});
    await assert.rejects(env.run("api.updateProfile({email:'invalid'})"), e => e.message === expected);
  }
});
