import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {normalizeSettings, type PlaudPluginSettings} from './settings-schema.js';

export interface CliArgs {
	command: 'sync' | 'validate';
	vault?: string;
	folder?: string;
	tokenFile?: string;
	configFile?: string;
	verbose?: boolean;
}

const DEFAULT_CONFIG_PATH = join(homedir(), '.config', 'plaud-sync', 'config.json');
const DEFAULT_TOKEN_PATH = join(homedir(), '.secrets', 'plaud.txt');

export function parseArgs(argv: string[]): CliArgs {
	const args = argv.slice(2);
	const command = args[0] as 'sync' | 'validate' | undefined;

	if (!command || !['sync', 'validate'].includes(command)) {
		throw new Error('Usage: plaud-sync <sync|validate> [options]\n\nCommands:\n  sync       Sync Plaud recordings to local markdown files\n  validate   Test that your Plaud API token is valid\n\nOptions:\n  --vault <path>        Base directory for output (default: current dir)\n  --folder <name>       Subfolder for notes (default: from config or "Plaud")\n  --token-file <path>   Path to token file (default: ~/.secrets/plaud.txt)\n  --config <path>       Config file path (default: ~/.config/plaud-sync/config.json)\n  --verbose             Enable verbose logging');
	}

	const result: CliArgs = {command};

	for (let i = 1; i < args.length; i++) {
		switch (args[i]) {
			case '--vault':
				result.vault = args[++i];
				break;
			case '--folder':
				result.folder = args[++i];
				break;
			case '--token-file':
				result.tokenFile = args[++i];
				break;
			case '--config':
				result.configFile = args[++i];
				break;
			case '--verbose':
				result.verbose = true;
				break;
		}
	}

	return result;
}

export async function loadToken(tokenFile?: string): Promise<string> {
	const path = tokenFile ?? DEFAULT_TOKEN_PATH;
	try {
		const content = await readFile(path, 'utf-8');
		const token = content.trim();
		if (!token) {
			throw new Error(`Token file is empty: ${path}`);
		}
		return token;
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
			throw new Error(`Token file not found: ${path}\nCreate it with: mkdir -p ~/.secrets && echo 'YOUR_TOKEN' > ~/.secrets/plaud.txt`);
		}
		throw error;
	}
}

export async function loadConfig(configFile?: string): Promise<PlaudPluginSettings> {
	const path = configFile ?? DEFAULT_CONFIG_PATH;
	try {
		const content = await readFile(path, 'utf-8');
		return normalizeSettings(JSON.parse(content));
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
			return normalizeSettings({});
		}
		throw error;
	}
}
