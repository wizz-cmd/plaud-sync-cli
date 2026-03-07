import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {hydratePlaudDetailContent} from '../src/plaud-content-hydrator.js';

describe('hydratePlaudDetailContent', () => {
	it('returns detail unchanged when summary and transcript already exist', async () => {
		const detail = {
			id: '1',
			summary: 'Existing summary',
			transcript_text: 'Existing transcript'
		};

		const result = await hydratePlaudDetailContent(detail, async () => {
			throw new Error('Should not be called');
		});

		assert.equal(result.summary, 'Existing summary');
		assert.equal(result.transcript_text, 'Existing transcript');
	});

	it('fetches summary from content_list link', async () => {
		const detail = {
			id: '1',
			content_list: [
				{data_type: 'auto_sum_note', data_link: 'https://example.com/summary'}
			]
		};

		const result = await hydratePlaudDetailContent(detail, async (url) => {
			if (url === 'https://example.com/summary') {
				return {summary: 'Fetched summary'};
			}
			throw new Error('Unexpected URL');
		});

		assert.equal(result.summary, 'Fetched summary');
	});

	it('fetches transcript from content_list link', async () => {
		const detail = {
			id: '1',
			summary: 'Has summary',
			content_list: [
				{data_type: 'transaction', data_link: 'https://example.com/transcript'}
			]
		};

		const result = await hydratePlaudDetailContent(detail, async (url) => {
			if (url === 'https://example.com/transcript') {
				return 'Full transcript text';
			}
			throw new Error('Unexpected URL');
		});

		assert.equal(result.transcript_text, 'Full transcript text');
	});

	it('handles fetch failure gracefully', async () => {
		const detail = {
			id: '1',
			content_list: [
				{data_type: 'auto_sum_note', data_link: 'https://example.com/fail'}
			]
		};

		const result = await hydratePlaudDetailContent(detail, async () => {
			throw new Error('Network error');
		});

		assert.equal(result.summary, undefined);
	});

	it('does not mutate original detail', async () => {
		const detail = {
			id: '1',
			content_list: [
				{data_type: 'auto_sum_note', data_link: 'https://example.com/summary'}
			]
		};

		await hydratePlaudDetailContent(detail, async () => ({summary: 'New'}));
		assert.equal(detail.summary, undefined);
	});
});
