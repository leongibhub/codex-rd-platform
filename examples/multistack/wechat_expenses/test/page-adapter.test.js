const test = require('node:test');
const assert = require('node:assert/strict');
const { createPageDefinition, STORAGE_KEY } = require('../pages/index/index');

function fakeWx(initialValue) {
  const values = new Map(initialValue === undefined ? [] : [[STORAGE_KEY, initialValue]]);
  return {
    getStorageSync(key) { return values.get(key); },
    setStorageSync(key, value) { values.set(key, value); },
    values,
  };
}

function pageFrom(definition) {
  return {
    ...definition,
    data: JSON.parse(JSON.stringify(definition.data)),
    setData(patch) { Object.assign(this.data, patch); },
  };
}

test('TC-MATRIX-WECHAT-004: Page adapter writes cents through an explicit wx fake', () => {
  const wxApi = fakeWx();
  const page = pageFrom(createPageDefinition(wxApi));
  page.onLoad();
  page.onAmountInput({ detail: { value: '12.34' } });
  page.onCategoryInput({ detail: { value: '餐饮' } });
  page.onAddExpense();
  const stored = wxApi.values.get(STORAGE_KEY);
  assert.equal(stored.length, 1);
  assert.equal(stored[0].amountCents, 1234);
  assert.equal(page.data.totalText, '12.34');
  assert.equal(page.data.error, '');
});

test('TC-MATRIX-WECHAT-005: a new Page adapter restores stored records and deletes them', () => {
  const wxApi = fakeWx([{ id: 'r_1', amountCents: 199, category: '交通', createdAt: '2026-09-06T00:00:00.000Z' }]);
  const page = pageFrom(createPageDefinition(wxApi));
  page.onLoad();
  assert.equal(page.data.records[0].amountText, '1.99');
  assert.equal(page.data.totalText, '1.99');
  page.onDeleteExpense({ currentTarget: { dataset: { id: 'r_1' } } });
  assert.deepEqual(wxApi.values.get(STORAGE_KEY), []);
  assert.equal(page.data.totalText, '0.00');
});

test('TC-MATRIX-WECHAT-006: corrupt local storage becomes an empty state', () => {
  const page = pageFrom(createPageDefinition(fakeWx({ bad: 'record' })));
  page.onLoad();
  assert.deepEqual(page.data.records, []);
  assert.equal(page.data.totalText, '0.00');
});

test('TC-MATRIX-WECHAT-008: overflow candidate is never written and a later load remains recoverable', () => {
  const original = [{
    id: 'r_limit', amountCents: Number.MAX_SAFE_INTEGER, category: '边界', createdAt: '2026-09-06T00:00:00.000Z',
  }];
  const wxApi = fakeWx(original);
  const page = pageFrom(createPageDefinition(wxApi));
  assert.doesNotThrow(() => page.onLoad());
  assert.equal(page.data.records.length, 1);
  assert.equal(page.data.error, '');
  page.onAmountInput({ detail: { value: '0.01' } });
  page.onCategoryInput({ detail: { value: '餐饮' } });
  page.onAddExpense();
  assert.deepEqual(wxApi.values.get(STORAGE_KEY), original);
  assert.match(page.data.error, /合计超出/);
  const reloaded = pageFrom(createPageDefinition(wxApi));
  assert.doesNotThrow(() => reloaded.onLoad());
  assert.equal(reloaded.data.records.length, 1);
  assert.equal(reloaded.data.error, '');

  const damaged = original.concat([{ id: 'r_overflow', amountCents: 1, category: '餐饮', createdAt: '2026-09-06T00:00:01.000Z' }]);
  const damagedWx = fakeWx(damaged);
  const recovered = pageFrom(createPageDefinition(damagedWx));
  assert.doesNotThrow(() => recovered.onLoad());
  assert.equal(recovered.data.records.length, 0);
  assert.match(recovered.data.error, /本地记录/);
  assert.deepEqual(damagedWx.values.get(STORAGE_KEY), damaged);
});
