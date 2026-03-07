import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {shouldSyncFile, isTrashedFile, runPlaudSync} from '../src/plaud-sync.js';
import type {PlaudFileSummary, PlaudApiClient} from '../src/plaud-api.js';
import type {PlaudVaultAdapter} from '../src/plaud-vault.js';

describe('isTrashedFile', () => {
	it('returns true for is_trash === true', () => {
		assert.equal(isTrashedFile({id: '1', is_trash: true}), true);
	});

	it('returns false for is_trash === false', () => {
		assert.equal(isTrashedFile({id: '1', is_trash: false}), false);
	});

	it('returns false for undefined is_trash', () => {
		assert.equal(isTrashedFile({id: '1'}), false);
	});
});

describe('shouldSyncFile', () => {
	it('excludes trashed files', () => {
		assert.equal(shouldSyncFile({id: '1', is_trash: true, start_time: 999999999999}, 0), false);
	});

	it('includes all non-trashed files when checkpoint is 0', () => {
		assert.equal(shouldSyncFile({id: '1', start_time: 100}, 0), true);
	});

	it('includes files newer than checkpoint', () => {
		assert.equal(shouldSyncFile({id: '1', start_time: 2000}, 1000), true);
	});

	it('excludes files older than checkpoint', () => {
		assert.equal(shouldSyncFile({id: '1', start_time: 500}, 1000), false);
	});

	it('includes files without start_time when checkpoint exists', () => {
		assert.equal(shouldSyncFile({id: '1'}, 1000), true);
	});
});

describe('runPlaudSync', () => {
	function createMockApi(files: PlaudFileSummary[], details: Record<string, Record<string, unknown>>): PlaudApiClient {
		return {
			listFiles: async () => files,
			getFileDetail: async (fileId) => {
				const d = details[fileId];
				if (!d) throw new Error(`No detail for ${fileId}`);
				return {id: fileId, file_id: fileId, ...d};
			}
		};
	}

	function createMockVault(): PlaudVaultAdapter {
		const store = new Map<string, string>();
		return {
			ensureFolder: async () => {},
			listMarkdownFiles: async () => [],
			read: async (path) => store.get(path) ?? '',
			write: async (path, content) => { store.set(path, content); },
			create: async (path, content) => { store.set(path, content); }
		};
	}

	it('syncs new files and advances checkpoint', async () => {
		const api = createMockApi(
			[{id: 'f1', file_id: 'f1', start_time: 1000}],
			{f1: {file_name: 'Test', start_time: 1000, duration: 60000}}
		);

		let savedCheckpoint = 0;
		const summary = await runPlaudSync({
			api,
			vault: createMockVault(),
			settings: {syncFolder: 'Plaud', filenamePattern: '{title}', updateExisting: true, lastSyncAtMs: 0},
			saveCheckpoint: async (ms) => { savedCheckpoint = ms; },
			normalizeDetail: (raw) => ({
				id: 'f1', fileId: 'f1', title: 'Test', startAtMs: 1000,
				durationMs: 60000, summary: 'Sum', highlights: [], transcript: 'Trans',
				raw: raw as Record<string, unknown>
			}),
			renderMarkdown: () => '---\nfile_id: f1\n---\n# Test',
			upsertNote: async () => ({action: 'created', path: 'Plaud/test.md'})
		});

		assert.equal(summary.listed, 1);
		assert.equal(summary.selected, 1);
		assert.equal(summary.created, 1);
		assert.equal(summary.failed, 0);
		assert.equal(savedCheckpoint, 1000);
	});

	it('does not advance checkpoint on failure', async () => {
		const api: PlaudApiClient = {
			listFiles: async () => [{id: 'f1', start_time: 2000}],
			getFileDetail: async () => { throw new Error('API down'); }
		};

		let savedCheckpoint = 0;
		const summary = await runPlaudSync({
			api,
			vault: createMockVault(),
			settings: {syncFolder: 'Plaud', filenamePattern: '{title}', updateExisting: true, lastSyncAtMs: 0},
			saveCheckpoint: async (ms) => { savedCheckpoint = ms; },
			normalizeDetail: () => { throw new Error('should not be called'); },
			renderMarkdown: () => '',
			upsertNote: async () => ({action: 'created', path: ''})
		});

		assert.equal(summary.failed, 1);
		assert.equal(savedCheckpoint, 0);
		assert.equal(summary.lastSyncAtMsAfter, 0);
	});

	it('skips trashed files', async () => {
		const api = createMockApi(
			[{id: 'f1', is_trash: true, start_time: 1000}],
			{}
		);

		const summary = await runPlaudSync({
			api,
			vault: createMockVault(),
			settings: {syncFolder: 'Plaud', filenamePattern: '{title}', updateExisting: true, lastSyncAtMs: 0},
			saveCheckpoint: async () => {},
			normalizeDetail: () => { throw new Error('should not be called'); },
			renderMarkdown: () => '',
			upsertNote: async () => ({action: 'created', path: ''})
		});

		assert.equal(summary.listed, 1);
		assert.equal(summary.selected, 0);
	});
});
