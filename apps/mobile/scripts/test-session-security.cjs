const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function load(file, modules) {
  const output = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const sandbox = { exports: {}, process: { env: {} }, require: (name) => {
    if (!(name in modules)) throw new Error(`Unexpected dependency ${name}`);
    return modules[name];
  } };
  vm.runInNewContext(output, sandbox);
  return sandbox.exports;
}
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
};
const tick = () => new Promise(setImmediate);
function fixture() {
  const tokens = new Map(); const pending = deferred(); const requests = [];
  let response, refreshCount = 0;
  const client = (config) => { requests.push(config); return Promise.resolve({ config }); };
  client.defaults = { headers: { common: {} } };
  client.interceptors = { request: { use() {} }, response: { use(_, failure) { response = failure; } } };
  const events = load('src/services/sessionEvents.ts', {});
  const api = load('src/services/api.ts', {
    axios: { create: () => client, default: { post: () => { refreshCount++; return pending.promise; } } },
    '../utils/secureStorage': {
      getItemAsync: async (key) => tokens.get(key) ?? null,
      setItemAsync: async (key, value) => { tokens.set(key, value); },
      deleteItemAsync: async (key) => { tokens.delete(key); },
    },
    'expo-constants': { default: { expoConfig: { hostUri: 'localhost:8081' } } },
    'react-native': { Platform: { OS: 'ios' } }, './sessionEvents': events,
  });
  const error = () => ({ response: { status: 401 }, config: { url: '/scans', headers: {} } });
  return { api, tokens, pending, requests, events, error, fail: (err) => response(err), count: () => refreshCount };
}
async function main() {
  {
    const f = fixture(); await f.api.saveTokens('old-access', 'old-refresh');
    const first = f.error(), second = f.error();
    const a = f.fail(first), b = f.fail(second); await tick();
    f.pending.resolve({ data: { data: { accessToken: 'new-access', refreshToken: 'new-refresh' } } });
    await Promise.all([a, b]);
    assert.equal(f.count(), 1); assert.equal(f.requests.length, 2);
    assert.equal(first.config._retry, true); assert.equal(second.config._retry, true);
    await assert.rejects(f.fail({ ...second, config: f.requests[0] }));
    assert.equal(f.count(), 1);
    assert.equal(await f.api.getRefreshToken(), 'new-refresh');
  }
  {
    const f = fixture(); await f.api.saveTokens('access', 'refresh'); let cleared = 0;
    f.events.onSessionCleared(() => { cleared++; });
    const request = f.fail(f.error()); const rejected = assert.rejects(request); await tick();
    f.pending.reject(new Error('expired')); await rejected;
    assert.equal(cleared, 1); assert.equal(f.tokens.size, 0);
  }
  for (const action of ['logout', 'new-login']) {
    const f = fixture(); await f.api.saveTokens('old-access', 'old-refresh');
    const request = f.fail(f.error()); const rejected = assert.rejects(request); await tick();
    if (action === 'logout') await f.api.clearTokens();
    else await f.api.saveTokens('other-access', 'other-refresh');
    f.pending.resolve({ data: { data: { accessToken: 'late-access', refreshToken: 'late-refresh' } } });
    await rejected;
    assert.equal(await f.api.getAccessToken(), action === 'logout' ? null : 'other-access');
    assert.equal(await f.api.getRefreshToken(), action === 'logout' ? null : 'other-refresh');
  }
  {
    const f = fixture(); let revoked;
    const create = (initialize) => {
      let state; const set = (update) => { state = { ...state, ...update }; };
      state = initialize(set); const store = () => state;
      store.setState = set; store.getState = () => state; return store;
    };
    const store = load('src/store/authStore.ts', {
      zustand: { create }, '../services/api': f.api, '../services/sessionEvents': f.events,
      '../services/authService': { default: { logout: async (token) => { revoked = token; await f.api.clearTokens(); } } },
    }).default;
    store.getState().acceptAuth({ user: { id: 'owner' }, accessToken: 'stale', refreshToken: 'stale' });
    await f.api.saveTokens('rotated-access', 'rotated-refresh'); await store.getState().logout();
    assert.equal(revoked, 'rotated-refresh'); assert.equal(store.getState().user, null);
    store.getState().acceptAuth({ user: { id: 'owner' }, accessToken: 'a', refreshToken: 'r' });
    await f.api.clearTokens(); assert.equal(store.getState().isAuthenticated, false); assert.equal(store.getState().user, null);
  }
  {
    const f = fixture(); const waiting = deferred();
    const create = (initialize) => {
      let state; const set = (update) => { state = { ...state, ...(typeof update === 'function' ? update(state) : update) }; };
      state = initialize(set); const store = () => state; store.setState = set; store.getState = () => state; return store;
    };
    const scans = load('src/store/scanStore.ts', {
      zustand: { create }, '../services/sessionEvents': f.events,
      '../services/scanService': { default: { createScan: () => waiting.promise, getRecentScans: () => waiting.promise } },
    }).default;
    const medicines = load('src/store/medicationStore.ts', {
      zustand: { create }, '../services/sessionEvents': f.events,
      '../utils/errorMessage': { errorMessage: (error) => error.message },
      '../services/medicationService': { default: { analyzePrescription: () => waiting.promise, getHistory: () => waiting.promise } },
    }).default;
    await f.api.saveTokens('old', 'refresh');
    scans.setState({ currentScan: { id: 'private' }, recentScans: [{ id: 'private' }] });
    medicines.setState({ currentPrescription: { text: 'private' }, history: [{ id: 'private' }] });
    const scan = assert.rejects(scans.getState().submitScan('SkinDisease', 'fixture'));
    const prescription = assert.rejects(medicines.getState().analyzePrescription('fixture'));
    const history = medicines.getState().loadHistory(); const recent = scans.getState().loadRecentScans();
    await f.api.saveTokens('other-account', 'other-refresh');
    assert.equal(scans.getState().currentScan, null); assert.equal(medicines.getState().currentPrescription, null);
    waiting.resolve({ id: 'old-private-result', items: [{ id: 'old-private-result' }] });
    await Promise.all([scan, prescription, history, recent]);
    assert.equal(scans.getState().recentScans.length, 0); assert.equal(medicines.getState().history.length, 0);
    assert.equal(scans.getState().error, null); assert.equal(medicines.getState().error, null);
  }
  {
    const f = fixture(); const waiting = deferred();
    const service = load('src/services/authService.ts', {
      './api': { ...f.api, default: { post: () => waiting.promise } }, './sessionEvents': f.events,
    }).default;
    const login = assert.rejects(service.login({ email: 'fixture@example.com', password: 'fixture' }));
    await f.api.clearTokens();
    waiting.resolve({ data: { success: true, data: { accessToken: 'late', refreshToken: 'late', user: {} } } });
    await login; assert.equal(await f.api.getAccessToken(), null);
  }
  console.log('PASS: concurrent refresh, retry limit, expiry cleanup, login/logout races, latest-token revocation and private-store isolation');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
