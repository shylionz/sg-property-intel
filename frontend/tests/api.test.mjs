import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fetchAllRentals, fetchAllTransactions } from '../src/lib/api.ts';

test('loads all pages including rows beyond the old 100-record sample', async () => {
  const requested = [];
  globalThis.fetch = async (url) => {
    requested.push(url);
    const page = Number(new URL(url).searchParams.get('page'));
    return {ok: true, json: async () => ({total: 205, data: Array.from({length: page < 2 ? 100 : 5}, (_, i) => ({monthly_rent: page * 100 + i}))})};
  };
  const rows = await fetchAllRentals('THE ANCHORAGE');
  assert.equal(rows.length, 205);
  assert.equal(rows[204].monthly_rent, 204);
  assert.equal(requested.length, 3);
  assert.ok(requested.every(url => url.includes('refresh_data=false')));
});

test('never accepts a partial or changing snapshot', async () => {
  for (const second of [{total: 101, data: []}, {total: 102, data: [{monthly_rent: 1}]}]) {
    let count = 0;
    globalThis.fetch = async () => ({ok:true, json:async () => count++ ? second : {total:101, data: Array(100).fill({})}});
    await assert.rejects(fetchAllRentals('THE ANCHORAGE'), /changed while loading/);
  }
});

test('sales table pagination does not trigger a source refresh per page', async () => {
  globalThis.fetch = async (url) => {
    assert.ok(url.includes('refresh_data=false'));
    return {ok: true, json:async () => ({total: 0, data: []})};
  };
  assert.deepEqual(await fetchAllTransactions('THE ANCHORAGE'), []);
});

test('an HTTP failure is visible rather than returning a partial dataset', async () => {
  globalThis.fetch = async () => ({ok: false});
  await assert.rejects(fetchAllRentals('THE ANCHORAGE'), /Failed to fetch rentals/);
});
