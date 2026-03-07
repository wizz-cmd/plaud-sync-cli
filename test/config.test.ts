import {describe, it} from 'node:test';
import assert from 'node:assert/strict';
import {parseArgs} from '../src/config.js';

describe('parseArgs', () => {
	it('parses sync command', () => {
		const result = parseArgs(['node', 'cli.js', 'sync']);
		assert.equal(result.command, 'sync');
	});

	it('parses validate command', () => {
		const result = parseArgs(['node', 'cli.js', 'validate']);
		assert.equal(result.command, 'validate');
	});

	it('throws on missing command', () => {
		assert.throws(() => parseArgs(['node', 'cli.js']), /Usage/);
	});

	it('throws on invalid command', () => {
		assert.throws(() => parseArgs(['node', 'cli.js', 'invalid']), /Usage/);
	});

	it('parses --vault option', () => {
		const result = parseArgs(['node', 'cli.js', 'sync', '--vault', '/tmp/vault']);
		assert.equal(result.vault, '/tmp/vault');
	});

	it('parses --folder option', () => {
		const result = parseArgs(['node', 'cli.js', 'sync', '--folder', 'Notes/Plaud']);
		assert.equal(result.folder, 'Notes/Plaud');
	});

	it('parses --token-file option', () => {
		const result = parseArgs(['node', 'cli.js', 'sync', '--token-file', '/etc/token']);
		assert.equal(result.tokenFile, '/etc/token');
	});

	it('parses --config option', () => {
		const result = parseArgs(['node', 'cli.js', 'sync', '--config', '/etc/config.json']);
		assert.equal(result.configFile, '/etc/config.json');
	});

	it('parses --verbose flag', () => {
		const result = parseArgs(['node', 'cli.js', 'sync', '--verbose']);
		assert.equal(result.verbose, true);
	});

	it('parses multiple options together', () => {
		const result = parseArgs([
			'node', 'cli.js', 'sync',
			'--vault', '/home/user/notes',
			'--folder', 'meetings',
			'--verbose'
		]);
		assert.equal(result.command, 'sync');
		assert.equal(result.vault, '/home/user/notes');
		assert.equal(result.folder, 'meetings');
		assert.equal(result.verbose, true);
	});
});
