import {readFile, writeFile} from 'node:fs/promises';
import {join} from 'node:path';

const STATE_FILE = '.plaud-sync-state.json';

export interface SyncState {
	lastSyncAtMs: number;
}

export async function loadState(baseDir: string, folder: string): Promise<SyncState> {
	const path = join(baseDir, folder, STATE_FILE);
	try {
		const content = await readFile(path, 'utf-8');
		const data = JSON.parse(content) as Record<string, unknown>;
		const lastSyncAtMs = typeof data.lastSyncAtMs === 'number' ? data.lastSyncAtMs : 0;
		return {lastSyncAtMs};
	} catch {
		return {lastSyncAtMs: 0};
	}
}

export async function saveState(baseDir: string, folder: string, state: SyncState): Promise<void> {
	const {mkdir} = await import('node:fs/promises');
	const dir = join(baseDir, folder);
	await mkdir(dir, {recursive: true});
	const path = join(dir, STATE_FILE);
	await writeFile(path, JSON.stringify(state, null, 2) + '\n', 'utf-8');
}
