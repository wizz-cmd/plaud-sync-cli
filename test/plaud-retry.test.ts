import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {withRetry, sanitizeTelemetryMessage} from '../src/plaud-retry.js';
import {PlaudApiError} from '../src/plaud-api.js';

describe('sanitizeTelemetryMessage', () => {
	it('redacts bearer tokens', () => {
		const result = sanitizeTelemetryMessage('Auth: Bearer abc123.xyz');
		assert.equal(result, 'Auth: Bearer [REDACTED]');
	});

	it('leaves non-token messages unchanged', () => {
		const result = sanitizeTelemetryMessage('Normal message');
		assert.equal(result, 'Normal message');
	});
});

describe('withRetry', () => {
	it('returns on first success', async () => {
		const result = await withRetry('test', async () => 42, {
			sleep: async () => {}
		});
		assert.equal(result, 42);
	});

	it('retries transient errors', async () => {
		let attempts = 0;
		const result = await withRetry('test', async () => {
			attempts++;
			if (attempts < 2) {
				throw new PlaudApiError('network', 'fail');
			}
			return 'ok';
		}, {
			policy: {maxAttempts: 3, baseDelayMs: 1, maxDelayMs: 1},
			sleep: async () => {}
		});

		assert.equal(result, 'ok');
		assert.equal(attempts, 2);
	});

	it('does not retry permanent errors', async () => {
		let attempts = 0;
		await assert.rejects(async () => {
			await withRetry('test', async () => {
				attempts++;
				throw new PlaudApiError('auth', 'unauthorized');
			}, {
				policy: {maxAttempts: 3, baseDelayMs: 1, maxDelayMs: 1},
				sleep: async () => {}
			});
		}, (error: unknown) => {
			assert.ok(error instanceof PlaudApiError);
			assert.equal(error.category, 'auth');
			return true;
		});

		assert.equal(attempts, 1);
	});

	it('throws after max attempts for transient errors', async () => {
		let attempts = 0;
		await assert.rejects(async () => {
			await withRetry('test', async () => {
				attempts++;
				throw new PlaudApiError('server', 'down');
			}, {
				policy: {maxAttempts: 2, baseDelayMs: 1, maxDelayMs: 1},
				sleep: async () => {}
			});
		});

		assert.equal(attempts, 2);
	});

	it('calls onRetry callback', async () => {
		const events: string[] = [];
		let attempts = 0;

		await withRetry('test-op', async () => {
			attempts++;
			if (attempts < 2) throw new PlaudApiError('network', 'timeout');
			return 'done';
		}, {
			policy: {maxAttempts: 3, baseDelayMs: 1, maxDelayMs: 1},
			sleep: async () => {},
			onRetry: (event) => events.push(event.operation)
		});

		assert.deepEqual(events, ['test-op']);
	});
});
