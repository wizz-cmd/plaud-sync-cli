import {createPlaudApiClient, type PlaudApiClient} from './plaud-api.js';

export interface CreateFetchPlaudApiClientOptions {
	apiDomain: string;
	token: string;
}

export function createFetchPlaudApiClient(options: CreateFetchPlaudApiClientOptions): PlaudApiClient {
	return createPlaudApiClient({
		apiDomain: options.apiDomain,
		token: options.token,
		request: async (req) => {
			const response = await fetch(req.url, {
				method: req.method ?? 'GET',
				headers: req.headers
			});

			let json: unknown;
			try {
				json = await response.json();
			} catch {
				json = null;
			}

			return {status: response.status, json};
		}
	});
}
