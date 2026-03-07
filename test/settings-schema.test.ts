import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeSettings, DEFAULT_SETTINGS} from '../src/settings-schema.js';

describe('normalizeSettings', () => {
	it('returns defaults for empty input', () => {
		const result = normalizeSettings({});
		assert.deepEqual(result, DEFAULT_SETTINGS);
	});

	it('returns defaults for null input', () => {
		const result = normalizeSettings(null);
		assert.deepEqual(result, DEFAULT_SETTINGS);
	});

	it('preserves valid settings', () => {
		const input = {
			apiDomain: 'https://custom.api.com',
			syncFolder: 'MyFolder',
			syncOnStartup: false,
			updateExisting: false,
			filenamePattern: '{date}-{title}',
			lastSyncAtMs: 1000
		};
		const result = normalizeSettings(input);
		assert.deepEqual(result, input);
	});

	it('falls back for invalid types', () => {
		const result = normalizeSettings({
			apiDomain: 123,
			syncFolder: '',
			syncOnStartup: 'yes',
			updateExisting: null,
			filenamePattern: undefined,
			lastSyncAtMs: -5
		});

		assert.equal(result.apiDomain, DEFAULT_SETTINGS.apiDomain);
		assert.equal(result.syncFolder, DEFAULT_SETTINGS.syncFolder);
		assert.equal(result.syncOnStartup, DEFAULT_SETTINGS.syncOnStartup);
		assert.equal(result.updateExisting, DEFAULT_SETTINGS.updateExisting);
		assert.equal(result.filenamePattern, DEFAULT_SETTINGS.filenamePattern);
		assert.equal(result.lastSyncAtMs, DEFAULT_SETTINGS.lastSyncAtMs);
	});
});
