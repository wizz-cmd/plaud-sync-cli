#!/usr/bin/env node

import {resolve} from 'node:path';
import {parseArgs, loadToken, loadConfig} from './config.js';
import {loadState, saveState} from './state.js';
import {createFetchPlaudApiClient} from './plaud-api-fetch.js';
import {createFsVaultAdapter} from './fs-vault-adapter.js';
import {normalizePlaudDetail} from './plaud-normalizer.js';
import {renderPlaudMarkdown} from './plaud-renderer.js';
import {runPlaudSync, isTrashedFile} from './plaud-sync.js';
import {upsertPlaudNote} from './plaud-vault.js';
import {withRetry, DEFAULT_RETRY_POLICY, sanitizeTelemetryMessage} from './plaud-retry.js';
import {hydratePlaudDetailContent} from './plaud-content-hydrator.js';
import {PlaudApiError, type PlaudApiClient, type PlaudFileDetail} from './plaud-api.js';

let verbose = false;

function log(message: string): void {
	if (verbose) {
		process.stderr.write(`[plaud-sync] ${message}\n`);
	}
}

function logError(message: string): void {
	process.stderr.write(`[plaud-sync] ERROR: ${message}\n`);
}

function toActionableMessage(error: unknown): string {
	if (error instanceof PlaudApiError) {
		if (error.category === 'auth') return 'authentication failed. Check your token.';
		if (error.category === 'rate_limit') return 'rate limited by Plaud API. Wait and retry.';
		if (error.category === 'network') return 'network error. Check your connection.';
		if (error.category === 'server') return 'Plaud API temporarily unavailable. Retry shortly.';
		if (error.category === 'invalid_response') return 'unexpected API response. Retry or check logs.';
	}

	if (error instanceof Error) {
		return sanitizeTelemetryMessage(error.message);
	}

	return 'Unknown error';
}

async function fetchSignedContent(url: string): Promise<unknown> {
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`Signed content fetch failed with HTTP ${response.status}.`);
	}

	const text = await response.text();
	if (!text.trim()) return '';

	try {
		return JSON.parse(text);
	} catch {
		return text;
	}
}

async function retryApiCall<T>(operation: string, execute: () => Promise<T>): Promise<T> {
	return withRetry(operation, execute, {
		policy: DEFAULT_RETRY_POLICY,
		onRetry: (event) => {
			log(`retry ${event.operation} attempt=${event.attempt}/${event.maxAttempts} delay=${event.delayMs}ms category=${event.category ?? 'unknown'}`);
		}
	});
}

async function cmdSync(args: {vault?: string; folder?: string; tokenFile?: string; configFile?: string}): Promise<void> {
	const config = await loadConfig(args.configFile);
	const token = await loadToken(args.tokenFile);
	const baseDir = resolve(args.vault ?? '.');
	const syncFolder = args.folder ?? config.syncFolder;

	log(`vault=${baseDir} folder=${syncFolder}`);

	const state = await loadState(baseDir, syncFolder);
	log(`checkpoint=${state.lastSyncAtMs} (${state.lastSyncAtMs ? new Date(state.lastSyncAtMs).toISOString() : 'none'})`);

	const api = createFetchPlaudApiClient({apiDomain: config.apiDomain, token});
	const resilientApi: PlaudApiClient = {
		listFiles: () => retryApiCall('sync.list_files', () => api.listFiles()),
		getFileDetail: async (fileId: string) => {
			const detail = await retryApiCall(`sync.file_detail.${fileId}`, () => api.getFileDetail(fileId));
			const hydrated = await hydratePlaudDetailContent(detail, async (url) => {
				return retryApiCall(`sync.content_fetch.${fileId}`, () => fetchSignedContent(url));
			});

			if (typeof hydrated.id === 'string' && hydrated.id.trim().length > 0) {
				return hydrated as PlaudFileDetail;
			}
			return detail;
		}
	};

	const vault = createFsVaultAdapter(baseDir);

	const summary = await runPlaudSync({
		api: resilientApi,
		vault,
		settings: {
			syncFolder,
			filenamePattern: config.filenamePattern,
			updateExisting: config.updateExisting,
			lastSyncAtMs: state.lastSyncAtMs
		},
		saveCheckpoint: async (nextLastSyncAtMs) => {
			await saveState(baseDir, syncFolder, {lastSyncAtMs: nextLastSyncAtMs});
		},
		normalizeDetail: normalizePlaudDetail,
		renderMarkdown: renderPlaudMarkdown,
		upsertNote: upsertPlaudNote
	});

	if (verbose || summary.failed > 0) {
		const msg = `sync complete: listed=${summary.listed} selected=${summary.selected} created=${summary.created} updated=${summary.updated} skipped=${summary.skipped} failed=${summary.failed}`;
		if (summary.failed > 0) {
			logError(msg);
			for (const f of summary.failures) {
				logError(`  file=${f.fileId}: ${f.message}`);
			}
		} else {
			log(msg);
		}
	}

	if (summary.failed > 0) {
		process.exitCode = 1;
	}
}

async function cmdValidate(args: {tokenFile?: string; configFile?: string}): Promise<void> {
	const config = await loadConfig(args.configFile);
	const token = await loadToken(args.tokenFile);

	const api = createFetchPlaudApiClient({apiDomain: config.apiDomain, token});
	const files = await retryApiCall('validate.list_files', () => api.listFiles());
	const activeCount = files.filter((file) => !isTrashedFile(file)).length;

	process.stdout.write(`Token valid. Active recordings: ${activeCount}\n`);
}

async function main(): Promise<void> {
	const args = parseArgs(process.argv);
	verbose = args.verbose ?? false;

	if (args.command === 'sync') {
		await cmdSync(args);
	} else if (args.command === 'validate') {
		await cmdValidate(args);
	}
}

main().catch((error) => {
	logError(toActionableMessage(error));
	process.exitCode = 1;
});
