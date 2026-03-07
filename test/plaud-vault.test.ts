import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {buildPlaudFilename, upsertPlaudNote, type PlaudVaultAdapter} from '../src/plaud-vault.js';

describe('buildPlaudFilename', () => {
	it('generates filename from pattern with date and title', () => {
		const result = buildPlaudFilename({filenamePattern: 'plaud-{date}-{title}', date: '2024-01-15', title: 'Team Standup'});
		assert.equal(result, 'plaud-2024-01-15-team-standup.md');
	});

	it('slugifies special characters in title', () => {
		const result = buildPlaudFilename({filenamePattern: '{title}', date: '2024-01-15', title: 'Hello World! @#$'});
		assert.equal(result, 'hello-world.md');
	});

	it('defaults to plaud-recording when pattern produces empty', () => {
		const result = buildPlaudFilename({filenamePattern: '', date: '2024-01-15', title: ''});
		assert.equal(result, 'plaud-2024-01-15-recording.md');
	});

	it('handles pattern without placeholders', () => {
		const result = buildPlaudFilename({filenamePattern: 'my-notes', date: '2024-01-15', title: 'Ignored'});
		assert.equal(result, 'my-notes.md');
	});
});

describe('upsertPlaudNote', () => {
	function createMockVault(files: Record<string, string> = {}): PlaudVaultAdapter {
		const store = new Map(Object.entries(files));
		return {
			ensureFolder: async () => {},
			listMarkdownFiles: async (folder) => {
				return [...store.keys()].filter((k) => k.startsWith(`${folder}/`) && k.endsWith('.md'));
			},
			read: async (path) => {
				const content = store.get(path);
				if (content === undefined) throw new Error(`Not found: ${path}`);
				return content;
			},
			write: async (path, content) => {
				store.set(path, content);
			},
			create: async (path, content) => {
				store.set(path, content);
			}
		};
	}

	it('creates a new note when none exists', async () => {
		const vault = createMockVault();
		const result = await upsertPlaudNote({
			vault,
			syncFolder: 'Plaud',
			filenamePattern: 'plaud-{date}-{title}',
			updateExisting: true,
			fileId: 'abc123',
			title: 'Meeting',
			date: '2024-01-15',
			markdown: '---\nfile_id: abc123\n---\n# Meeting'
		});

		assert.equal(result.action, 'created');
		assert.ok(result.path.includes('plaud-2024-01-15-meeting.md'));
	});

	it('updates existing note with matching file_id', async () => {
		const vault = createMockVault({
			'Plaud/existing.md': '---\nfile_id: abc123\ntitle: "Old"\n---\n# Old'
		});

		const result = await upsertPlaudNote({
			vault,
			syncFolder: 'Plaud',
			filenamePattern: 'plaud-{date}-{title}',
			updateExisting: true,
			fileId: 'abc123',
			title: 'Updated',
			date: '2024-01-15',
			markdown: '---\nfile_id: abc123\n---\n# Updated'
		});

		assert.equal(result.action, 'updated');
		assert.equal(result.path, 'Plaud/existing.md');
	});

	it('skips when updateExisting is false and note exists', async () => {
		const vault = createMockVault({
			'Plaud/existing.md': '---\nfile_id: abc123\n---\n# Old'
		});

		const result = await upsertPlaudNote({
			vault,
			syncFolder: 'Plaud',
			filenamePattern: 'plaud-{date}-{title}',
			updateExisting: false,
			fileId: 'abc123',
			title: 'Meeting',
			date: '2024-01-15',
			markdown: '---\nfile_id: abc123\n---\n# Meeting'
		});

		assert.equal(result.action, 'skipped');
	});

	it('handles filename collisions with suffix', async () => {
		const vault = createMockVault({
			'Plaud/plaud-2024-01-15-meeting.md': '---\nfile_id: other\n---\n# Other'
		});

		const result = await upsertPlaudNote({
			vault,
			syncFolder: 'Plaud',
			filenamePattern: 'plaud-{date}-{title}',
			updateExisting: true,
			fileId: 'new123',
			title: 'Meeting',
			date: '2024-01-15',
			markdown: '---\nfile_id: new123\n---\n# Meeting'
		});

		assert.equal(result.action, 'created');
		assert.ok(result.path.includes('-2.md'));
	});
});
