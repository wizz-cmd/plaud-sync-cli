import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {renderPlaudMarkdown} from '../src/plaud-renderer.js';
import type {NormalizedPlaudDetail} from '../src/plaud-normalizer.js';

function makeDetail(overrides: Partial<NormalizedPlaudDetail> = {}): NormalizedPlaudDetail {
	return {
		id: 'test-id',
		fileId: 'test-file-id',
		title: 'Test Recording',
		startAtMs: 1700000000000,
		durationMs: 300000,
		summary: 'A test summary.',
		highlights: ['Point 1', 'Point 2'],
		transcript: 'Speaker: Hello world',
		raw: {},
		...overrides
	};
}

describe('renderPlaudMarkdown', () => {
	it('renders complete markdown with frontmatter', () => {
		const md = renderPlaudMarkdown(makeDetail());
		assert.ok(md.startsWith('---\n'));
		assert.ok(md.includes('source: plaud'));
		assert.ok(md.includes('type: recording'));
		assert.ok(md.includes('file_id: test-file-id'));
		assert.ok(md.includes('title: "Test Recording"'));
		assert.ok(md.includes('# Test Recording'));
		assert.ok(md.includes('## Summary'));
		assert.ok(md.includes('A test summary.'));
		assert.ok(md.includes('## Highlights'));
		assert.ok(md.includes('- Point 1'));
		assert.ok(md.includes('- Point 2'));
		assert.ok(md.includes('## Transcript'));
		assert.ok(md.includes('Speaker: Hello world'));
	});

	it('formats date correctly', () => {
		const md = renderPlaudMarkdown(makeDetail({startAtMs: 1700000000000}));
		assert.ok(md.includes('date: 2023-11-14'));
	});

	it('formats duration in minutes', () => {
		const md = renderPlaudMarkdown(makeDetail({durationMs: 300000}));
		assert.ok(md.includes('duration: 5 min'));
	});

	it('uses default title when empty', () => {
		const md = renderPlaudMarkdown(makeDetail({title: ''}));
		assert.ok(md.includes('# Untitled recording'));
	});

	it('shows fallback for empty summary', () => {
		const md = renderPlaudMarkdown(makeDetail({summary: ''}));
		assert.ok(md.includes('No summary available.'));
	});

	it('shows fallback for empty transcript', () => {
		const md = renderPlaudMarkdown(makeDetail({transcript: ''}));
		assert.ok(md.includes('No transcript available.'));
	});

	it('shows fallback for empty highlights', () => {
		const md = renderPlaudMarkdown(makeDetail({highlights: []}));
		assert.ok(md.includes('- No highlights extracted.'));
	});

	it('escapes quotes in frontmatter title', () => {
		const md = renderPlaudMarkdown(makeDetail({title: 'Title with "quotes"'}));
		assert.ok(md.includes('title: "Title with \\"quotes\\""'));
	});

	it('handles zero/invalid timestamps', () => {
		const md = renderPlaudMarkdown(makeDetail({startAtMs: 0, durationMs: 0}));
		assert.ok(md.includes('date: 1970-01-01'));
		assert.ok(md.includes('duration: 0 min'));
	});
});
