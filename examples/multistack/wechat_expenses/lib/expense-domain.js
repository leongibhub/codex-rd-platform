'use strict';

const MAX_CENTS = Number.MAX_SAFE_INTEGER;

function parseAmountToCents(value) {
  const match = String(value == null ? '' : value).trim().match(/^([0-9]+)(?:\.([0-9]{1,2}))?$/);
  if (!match) throw new Error('金额必须是最多两位小数的正数');
  const whole = Number(match[1]);
  const fractional = Number((match[2] || '').padEnd(2, '0'));
  if (!Number.isSafeInteger(whole) || whole > Math.floor((MAX_CENTS - fractional) / 100)) {
    throw new Error('金额超出可安全记录的范围');
  }
  const cents = whole * 100 + fractional;
  if (cents <= 0) throw new Error('金额必须大于零');
  return cents;
}

function assertRecord(record) {
  if (!record || typeof record !== 'object' || typeof record.id !== 'string' || !record.id) {
    throw new Error('记录 ID 无效');
  }
  if (!Number.isSafeInteger(record.amountCents) || record.amountCents <= 0) {
    throw new Error('记录金额无效');
  }
  if (typeof record.category !== 'string' || !record.category.trim() || record.category.trim().length > 64) {
    throw new Error('记录分类无效');
  }
  if (typeof record.createdAt !== 'string' || !Number.isFinite(Date.parse(record.createdAt))) {
    throw new Error('记录时间无效');
  }
  return Object.freeze({
    id: record.id,
    amountCents: record.amountCents,
    category: record.category.trim(),
    createdAt: record.createdAt,
  });
}

function appendExpense(records, input, options) {
  const current = normalizeRecords(records);
  const category = String(input && input.category != null ? input.category : '').trim();
  if (!category || category.length > 64) throw new Error('分类不能为空且不得超过 64 个字符');
  const id = options.idFactory();
  const record = assertRecord({
    id,
    amountCents: parseAmountToCents(input && input.amount),
    category,
    createdAt: options.now(),
  });
  if (current.some((item) => item.id === record.id)) throw new Error('记录 ID 重复');
  const candidate = current.concat(record);
  totalCents(candidate);
  return candidate;
}

function removeExpense(records, id) {
  const current = normalizeRecords(records);
  if (typeof id !== 'string' || !id) return current;
  return current.filter((record) => record.id !== id);
}

function normalizeRecords(value) {
  if (!Array.isArray(value)) return [];
  try {
    const records = value.map(assertRecord);
    const ids = new Set(records.map((record) => record.id));
    return ids.size === records.length ? records : [];
  } catch (_) {
    return [];
  }
}

function totalCents(records) {
  return normalizeRecords(records).reduce((total, record) => {
    if (total > MAX_CENTS - record.amountCents) throw new Error('合计超出可安全记录的范围');
    return total + record.amountCents;
  }, 0);
}

function formatCents(cents) {
  if (!Number.isSafeInteger(cents) || cents < 0) throw new Error('金额分值无效');
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`;
}

module.exports = { appendExpense, formatCents, normalizeRecords, parseAmountToCents, removeExpense, totalCents };
