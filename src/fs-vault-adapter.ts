import {readdir, readFile, writeFile, mkdir, stat} from 'node:fs/promises';
import {join} from 'node:path';
import type {PlaudVaultAdapter} from './plaud-vault.js';

export function createFsVaultAdapter(baseDir: string): PlaudVaultAdapter {
	const resolve = (path: string) => join(baseDir, path);

	return {
		ensureFolder: async (folder) => {
			const normalized = folder.replace(/\/+$/, '').trim();
			if (!normalized) return;
			await mkdir(resolve(normalized), {recursive: true});
		},

		listMarkdownFiles: async (folder) => {
			const normalized = folder.replace(/\/+$/, '');
			const fullPath = resolve(normalized);

			try {
				await stat(fullPath);
			} catch {
				return [];
			}

			const entries = await readdir(fullPath);
			return entries
				.filter((entry) => entry.endsWith('.md'))
				.map((entry) => `${normalized}/${entry}`);
		},

		read: async (path) => {
			return readFile(resolve(path), 'utf-8');
		},

		write: async (path, content) => {
			await writeFile(resolve(path), content, 'utf-8');
		},

		create: async (path, content) => {
			const fullPath = resolve(path);
			const dir = fullPath.slice(0, fullPath.lastIndexOf('/'));
			await mkdir(dir, {recursive: true});
			await writeFile(fullPath, content, 'utf-8');
		}
	};
}
