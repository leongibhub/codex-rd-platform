const test = require('node:test');
const assert = require('node:assert/strict');

const domain = require('../lib/expense-domain');

test('TC-MATRIX-WECHAT-001: sums cents without floating-point drift', () => {
  let records = [];
  records = domain.appendExpense(records, { amount: '0.10', category: '餐饮' }, {
    idFactory: () => 'r_1', now: () => '2026-09-06T00:00:00.000Z',
  });
  records = domain.appendExpense(records, { amount: '0.20', category: '交通' }, {
    idFactory: () => 'r_2', now: () => '2026-09-06T00:00:01.000Z',
  });
  assert.equal(domain.totalCents(records), 30);
  assert.equal(domain.formatCents(30), '0.30');
});

test('TC-MATRIX-WECHAT-002: invalid amount or category never mutates records', () => {
  const original = [];
  for (const input of [
    { amount: '', category: '餐饮' }, { amount: '0', category: '餐饮' },
    { amount: '-1', category: '餐饮' }, { amount: '1.234', category: '餐饮' },
    { amount: '1e2', category: '餐饮' }, { amount: '1', category: '  ' },
  ]) {
    assert.throws(() => domain.appendExpense(original, input));
    assert.deepEqual(original, []);
  }
});

test('TC-MATRIX-WECHAT-003: rejects duplicate IDs and preserves unknown deletion', () => {
  const existing = [{ id: 'r_1', amountCents: 100, category: '餐饮', createdAt: '2026-09-06T00:00:00.000Z' }];
  assert.throws(() => domain.appendExpense(existing, { amount: '2', category: '交通' }, {
    idFactory: () => 'r_1', now: () => '2026-09-06T00:00:01.000Z',
  }));
  assert.deepEqual(domain.removeExpense(existing, 'does-not-exist'), existing);
  assert.deepEqual(domain.removeExpense(existing, 'r_1'), []);
});

test('TC-MATRIX-WECHAT-008: rejects an unsafe cumulative total without changing the source collection', () => {
  const existing = [{
    id: 'r_limit', amountCents: Number.MAX_SAFE_INTEGER, category: '边界', createdAt: '2026-09-06T00:00:00.000Z',
  }];
  assert.throws(() => domain.appendExpense(existing, { amount: '0.01', category: '餐饮' }, {
    idFactory: () => 'r_overflow', now: () => '2026-09-06T00:00:01.000Z',
  }), /合计超出/);
  assert.deepEqual(existing, [{
    id: 'r_limit', amountCents: Number.MAX_SAFE_INTEGER, category: '边界', createdAt: '2026-09-06T00:00:00.000Z',
  }]);
});
