"use strict";

const assert = require("assert");
const test = require("node:test");
const { createPageDefinition, STORAGE_KEY } = require("../../examples/multistack/wechat_expenses/pages/index/index");

function fakeWx(initial) {
  const values = new Map([[STORAGE_KEY, initial]]);
  return {
    getStorageSync(key) { return values.get(key); },
    setStorageSync(key, value) { values.set(key, value); },
    value() { return values.get(STORAGE_KEY); },
  };
}

function page(wxApi) {
  const definition = createPageDefinition(wxApi);
  const instance = { data: { ...definition.data }, setData(next) { this.data = { ...this.data, ...next }; } };
  for (const [key, value] of Object.entries(definition)) if (typeof value === "function") instance[key] = value;
  return instance;
}

test("TC-IQA-WECHAT-01: explicit wx stub stores cents and restores total", () => {
  const wxStub = fakeWx(undefined);
  const first = page(wxStub);
  first.onLoad();
  first.onAmountInput({ detail: { value: "0.10" } }); first.onCategoryInput({ detail: { value: "餐饮" } }); first.onAddExpense();
  first.onAmountInput({ detail: { value: "0.20" } }); first.onCategoryInput({ detail: { value: "出行" } }); first.onAddExpense();
  assert.deepEqual(wxStub.value().map((record) => record.amountCents), [10, 20]);
  assert.equal(first.data.totalText, "0.30");
  const restored = page(wxStub); restored.onLoad();
  assert.equal(restored.data.records.length, 2);
  assert.equal(restored.data.totalText, "0.30");
});

test("TC-IQA-WECHAT-02: invalid input does not write; delete and corrupt restore are safe", () => {
  const wxStub = fakeWx(undefined);
  const instance = page(wxStub); instance.onLoad();
  instance.onAmountInput({ detail: { value: "1.234" } }); instance.onCategoryInput({ detail: { value: "餐饮" } }); instance.onAddExpense();
  assert.equal(instance.data.records.length, 0);
  assert.match(instance.data.error, /金额/);
  instance.onAmountInput({ detail: { value: "1" } }); instance.onAddExpense();
  const id = instance.data.records[0].id;
  instance.onDeleteExpense({ currentTarget: { dataset: { id } } });
  assert.deepEqual(wxStub.value(), []);
  const corrupt = page(fakeWx([{ id: "bad", amountCents: -1, category: "x", createdAt: "nope" }])); corrupt.onLoad();
  assert.equal(corrupt.data.records.length, 0);
  assert.equal(corrupt.data.totalText, "0.00");
});

test("TC-IQA-WECHAT-03: cumulative cents overflow never persists a new record", () => {
  const baseline = [{ id: "max", amountCents: Number.MAX_SAFE_INTEGER, category: "已有", createdAt: "2026-09-06T00:00:00.000Z" }];
  const wxStub = fakeWx(baseline);
  const instance = page(wxStub); instance.onLoad();
  instance.onAmountInput({ detail: { value: "0.01" } }); instance.onCategoryInput({ detail: { value: "新增" } }); instance.onAddExpense();
  assert.deepEqual(wxStub.value(), baseline);
  assert.match(instance.data.error, /合计/);
});
