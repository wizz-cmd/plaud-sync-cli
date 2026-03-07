import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {normalizePlaudDetail} from '../src/plaud-normalizer.js';

describe('normalizePlaudDetail', () => {
	it('extracts id and fileId from raw detail', () => {
		const result = normalizePlaudDetail({id: 'abc', file_id: 'xyz'});
		assert.equal(result.id, 'abc');
		assert.equal(result.fileId, 'xyz');
	});

	it('falls back to id when file_id is missing', () => {
		const result = normalizePlaudDetail({id: 'abc'});
		assert.equal(result.fileId, 'abc');
	});

	it('falls back to file_id when id is missing', () => {
		const result = normalizePlaudDetail({file_id: 'xyz'});
		assert.equal(result.id, 'xyz');
	});

	it('defaults to unknown when both are missing', () => {
		const result = normalizePlaudDetail({});
		assert.equal(result.id, 'unknown');
		assert.equal(result.fileId, 'unknown');
	});

	it('extracts title from file_name', () => {
		const result = normalizePlaudDetail({id: '1', file_name: 'My Recording'});
		assert.equal(result.title, 'My Recording');
	});

	it('extracts title from filename fallback', () => {
		const result = normalizePlaudDetail({id: '1', filename: 'Alt Name'});
		assert.equal(result.title, 'Alt Name');
	});

	it('extracts summary from direct field', () => {
		const result = normalizePlaudDetail({id: '1', summary: 'A summary'});
		assert.equal(result.summary, 'A summary');
	});

	it('extracts summary from ai_content', () => {
		const result = normalizePlaudDetail({id: '1', ai_content: {summary: 'AI summary'}});
		assert.equal(result.summary, 'AI summary');
	});

	it('extracts transcript from trans_result.full_text', () => {
		const result = normalizePlaudDetail({id: '1', trans_result: {full_text: 'Hello world'}});
		assert.equal(result.transcript, 'Hello world');
	});

	it('reconstructs transcript from paragraphs array', () => {
		const result = normalizePlaudDetail({
			id: '1',
			trans_result: {
				paragraphs: [
					{speaker: 'Alice', text: 'Hello'},
					{speaker: 'Bob', text: 'Hi'}
				]
			}
		});
		assert.equal(result.transcript, 'Alice: Hello\nBob: Hi');
	});

	it('extracts highlights from array', () => {
		const result = normalizePlaudDetail({id: '1', highlights: ['Point 1', 'Point 2']});
		assert.deepEqual(result.highlights, ['Point 1', 'Point 2']);
	});

	it('extracts highlights from ai_notes.key_points', () => {
		const result = normalizePlaudDetail({id: '1', ai_notes: {key_points: ['KP1', 'KP2']}});
		assert.deepEqual(result.highlights, ['KP1', 'KP2']);
	});

	it('parses startAtMs and durationMs', () => {
		const result = normalizePlaudDetail({id: '1', start_time: 1700000000000, duration: 300000});
		assert.equal(result.startAtMs, 1700000000000);
		assert.equal(result.durationMs, 300000);
	});

	it('defaults timestamps to 0 for invalid values', () => {
		const result = normalizePlaudDetail({id: '1', start_time: -5, duration: 'nope'});
		assert.equal(result.startAtMs, 0);
		assert.equal(result.durationMs, 0);
	});

	it('handles non-object input gracefully', () => {
		const result = normalizePlaudDetail(null);
		assert.equal(result.id, 'unknown');
		assert.equal(result.summary, '');
		assert.equal(result.transcript, '');
	});
});
