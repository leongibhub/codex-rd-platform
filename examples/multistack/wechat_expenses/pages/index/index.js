'use strict';

const domain = require('../../lib/expense-domain');
const STORAGE_KEY = 'wechat-expenses.records.v1';
let sequence = 0;

function storageFor(wxApi) {
  if (!wxApi || typeof wxApi.getStorageSync !== 'function' || typeof wxApi.setStorageSync !== 'function') {
    throw new Error('微信本地存储接口不可用');
  }
  return {
    read() {
      try { return domain.normalizeRecords(wxApi.getStorageSync(STORAGE_KEY)); } catch (_) { return []; }
    },
    write(records) { wxApi.setStorageSync(STORAGE_KEY, records); },
  };
}

function toViewRecord(record) {
  return { ...record, amountText: domain.formatCents(record.amountCents) };
}

function pageState(records) {
  return { records: records.map(toViewRecord), totalText: domain.formatCents(domain.totalCents(records)) };
}

function createPageDefinition(wxApi) {
  const storage = storageFor(wxApi);
  return {
    data: { amountInput: '', categoryInput: '', records: [], totalText: '0.00', error: '' },
    onLoad() {
      try {
        this.setData({ ...pageState(storage.read()), error: '' });
      } catch (error) {
        this.setData({ records: [], totalText: '0.00', error: `本地记录无法安全加载：${error.message}` });
      }
    },
    onAmountInput(event) { this.setData({ amountInput: event.detail.value }); },
    onCategoryInput(event) { this.setData({ categoryInput: event.detail.value }); },
    onAddExpense() {
      try {
        const records = domain.appendExpense(storage.read(), {
          amount: this.data.amountInput,
          category: this.data.categoryInput,
        }, {
          idFactory: () => `r_${Date.now()}_${++sequence}`,
          now: () => new Date().toISOString(),
        });
        const nextState = pageState(records);
        storage.write(records);
        this.setData({ ...nextState, amountInput: '', categoryInput: '', error: '' });
      } catch (error) {
        this.setData({ error: error.message });
      }
    },
    onDeleteExpense(event) {
      const records = domain.removeExpense(storage.read(), event.currentTarget.dataset.id);
      const nextState = pageState(records);
      storage.write(records);
      this.setData({ ...nextState, error: '' });
    },
  };
}

if (typeof Page === 'function' && typeof wx !== 'undefined') Page(createPageDefinition(wx));
module.exports = { createPageDefinition, STORAGE_KEY };
