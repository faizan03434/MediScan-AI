const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
function load(file, modules) {
  const output = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const context = { exports: {}, require: (name) => {
    if (!(name in modules)) throw new Error(`Unexpected dependency: ${name}`);
    return modules[name];
  } };
  vm.runInNewContext(output, context);
  return context.exports;
}
const deferred = () => { let resolve; const promise = new Promise((done) => { resolve = done; }); return { promise, resolve }; };
function fixture(platform = 'ios', hold) {
  const scheduled = new Map(), shown = new Map(); const calls = []; const entered = deferred();
  const events = load('src/services/sessionEvents.ts', {});
  const api = {
    setNotificationHandler() {},
    SchedulableTriggerInputTypes: { DATE: 'date' },
    getAllScheduledNotificationsAsync: async () => [...scheduled.values()],
    getPresentedNotificationsAsync: async () => [...shown.values()],
    cancelScheduledNotificationAsync: async (id) => { scheduled.delete(id); },
    dismissNotificationAsync: async (id) => { shown.delete(id); },
    scheduleNotificationAsync: async (request) => {
      entered.resolve(); if (hold) await hold.promise;
      scheduled.set(request.identifier, request); calls.push(request);
    },
    getPermissionsAsync: async () => { throw new Error('Native notifications unavailable'); },
  };
  const hooks = load('src/hooks/useNotifications.ts', {
    'expo-notifications': api, 'react-native': { Platform: { OS: platform } },
    'expo-device': { isDevice: true }, '../services/sessionEvents': events,
  });
  return { hooks, events, scheduled, shown, calls, entered };
}
const scan = (type = 'Anemia') => ({ id: 'private-case', scanType: type,
  nextScanRecommendation: 'private symptoms and private-drug', nextScanDate: new Date(Date.now() + 86400000).toISOString() });
async function main() {
  {
    const f = fixture();
    f.scheduled.set('scan_reminder_Anemia', { identifier: 'scan_reminder_Anemia' });
    f.scheduled.set('scan_reminder_4_EyeDisease', { identifier: 'scan_reminder_4_EyeDisease' });
    const reminders = await f.hooks.getScheduledReminders();
    assert.equal(reminders.length, 1); assert.equal(reminders[0].identifier, 'scan_reminder_4_EyeDisease');
  }
  {
    const f = fixture(); await f.hooks.scheduleScanReminder(scan());
    const payload = JSON.stringify(f.calls[0].content);
    assert(!payload.includes('private')); assert(!payload.includes('Anemia'));
    f.shown.set('scan_reminder_SkinDisease', { request: { identifier: 'scan_reminder_SkinDisease' } });
    f.scheduled.set('other', { identifier: 'other-app-feature' });
    f.events.notifySessionCleared(); await f.hooks.getScheduledReminders();
    assert.equal(f.shown.size, 0); assert.equal(f.scheduled.size, 1); assert(f.scheduled.has('other'));
    assert.equal(await f.hooks.registerForPushNotificationsAsync(), null);
  }
  {
    const hold = deferred(); const f = fixture('ios', hold);
    const old = f.hooks.scheduleScanReminder(scan()); await f.entered.promise;
    f.events.notifySessionCleared(); const current = f.hooks.scheduleScanReminder(scan('EyeDisease'));
    hold.resolve(); await Promise.all([old, current]);
    const remaining = await f.hooks.getScheduledReminders();
    assert.equal(remaining.length, 1); assert(remaining[0].identifier.endsWith('_EyeDisease'));
  }
  {
    const f = fixture('web'); await f.hooks.scheduleScanReminder(scan());
    assert.equal(f.calls.length, 0); assert.equal(await f.hooks.registerForPushNotificationsAsync(), null);
    const native = fixture(); await native.hooks.scheduleScanReminder({ ...scan(), nextScanDate: 'invalid' });
    assert.equal(native.calls.length, 0);
  }
  // Inventory security coverage: newly added private routes must not be auto-discovered outside the guard.
  const source = ts.createSourceFile('root.tsx', fs.readFileSync('src/app/_layout.tsx', 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const guarded = new Set();
  function visit(node, protectedRoute = false) {
    if (ts.isJsxElement(node) && node.openingElement.tagName.getText(source) === 'Stack.Protected') {
      const guard = node.openingElement.attributes.properties.find((a) => a.name?.getText(source) === 'guard');
      assert.equal(guard?.initializer?.expression?.getText(source), 'authenticated');
      node.children.forEach((child) => visit(child, true)); return;
    }
    if (protectedRoute && ts.isJsxSelfClosingElement(node) && node.tagName.getText(source) === 'Stack.Screen') {
      const name = node.attributes.properties.find((a) => a.name?.getText(source) === 'name');
      if (name?.initializer && ts.isStringLiteral(name.initializer)) guarded.add(name.initializer.text);
    }
    ts.forEachChild(node, (child) => visit(child, protectedRoute));
  }
  visit(source);
  function inventory(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const file = path.join(directory, entry.name);
      if (entry.isDirectory()) { inventory(file); continue; }
      if (!entry.name.endsWith('.tsx') || entry.name === '_layout.tsx') continue;
      const route = path.relative('src/app', file).replaceAll('\\', '/').replace(/\.tsx$/, '');
      if (['index', 'deletion-status'].includes(route) || ['(auth)/', 'onboarding/', 'information/'].some((prefix) => route.startsWith(prefix))) continue;
      assert([...guarded].some((name) => route === name || route.startsWith(name + '/')), `Private route missing session guard: ${route}`);
    }
  }
  inventory('src/app');
  console.log('PASS: generic reminder payloads, logout/schedule races, cleanup, unsupported platforms and private-route coverage');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
