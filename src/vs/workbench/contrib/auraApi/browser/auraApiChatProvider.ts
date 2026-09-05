/*---------------------------------------------------------------------------------------------
 *  Aura API — провайдер языковых моделей для встроенного чата.
 *  Каждый пригодный ключ (не отклонённый проверкой) появляется в списке моделей
 *  чата как BYOK-модель; запросы уходят на его OpenAI-совместимый эндпоинт.
 *--------------------------------------------------------------------------------------------*/

import { Emitter, Event } from '../../../../base/common/event.js';
import { CancellationToken } from '../../../../base/common/cancellation.js';
import { canceled } from '../../../../base/common/errors.js';
import { Disposable } from '../../../../base/common/lifecycle.js';
import { ExtensionIdentifier } from '../../../../platform/extensions/common/extensions.js';
import { IConfigurationService } from '../../../../platform/configuration/common/configuration.js';
import { ILogService } from '../../../../platform/log/common/log.js';
import {
	ILanguageModelChatProvider, ILanguageModelChatMetadataAndIdentifier, ILanguageModelChatResponse,
	ILanguageModelChatRequestOptions, ILanguageModelChatInfoOptions, ILanguageModelChatMetadata,
	IChatResponsePart, ChatMessageRole,
} from '../../chat/common/languageModels.js';
import { IChatMessage } from '../../chat/common/languageModels.js';
import { IAuraApiKeysService, IAuraApiKey } from '../common/auraApiKeys.js';

export const AURA_API_VENDOR = 'auraApi';
export const AURA_API_VENDOR_DISPLAY_NAME = 'Aura API';
export const AURA_API_SYSTEM_PROMPT_SETTING = 'auraApi.chat.systemPrompt';

/** Идентификатор модели в сервисе моделей: `auraApi/<id ключа>`. */
export function toAuraModelIdentifier(keyId: string): string {
	return `${AURA_API_VENDOR}/${keyId}`;
}

/** Обратное преобразование: сервис зовёт `sendChatRequest` с полным идентификатором, а не с id ключа. */
function toKeyId(modelIdentifier: string): string {
	return modelIdentifier.startsWith(`${AURA_API_VENDOR}/`)
		? modelIdentifier.slice(AURA_API_VENDOR.length + 1)
		: modelIdentifier;
}

interface IOpenAIToolCall {
	id: string;
	type: 'function';
	function: { name: string; arguments: string };
}

interface IOpenAIMessage {
	role: 'system' | 'user' | 'assistant' | 'tool';
	content: string;
	tool_calls?: IOpenAIToolCall[];
	tool_call_id?: string;
}

/** Инструмент в формате, который приходит от ядра чата (`vscode.LanguageModelChatTool`). */
interface IChatRequestTool {
	readonly name: string;
	readonly description?: string;
	readonly inputSchema?: object;
}

/** Накопитель дельт tool_calls: OpenAI шлёт имя и аргументы по кускам, склеивая их по index. */
interface IToolCallAccumulator {
	id: string;
	name: string;
	arguments: string;
}

function partsToText(parts: readonly unknown[]): string {
	return parts
		.map(part => {
			const p = part as { type?: string; value?: unknown };
			return p.type === 'text' ? String(p.value ?? '') : '';
		})
		.filter(Boolean)
		.join('\n');
}

/** CSP воркбенча пропускает только https и локальный http — иначе запрос молча блокируется. */
function isBlockedByContentSecurityPolicy(baseUrl: string): boolean {
	if (!/^http:\/\//i.test(baseUrl)) {
		return false;
	}
	return !/^http:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/i.test(baseUrl);
}

export class AuraApiChatProvider extends Disposable implements ILanguageModelChatProvider {

	private readonly _onDidChange = this._register(new Emitter<void>());
	readonly onDidChange: Event<void> = this._onDidChange.event;

	constructor(
		private readonly keysService: IAuraApiKeysService,
		private readonly configurationService: IConfigurationService,
		private readonly logService: ILogService,
	) {
		super();
		this._register(this.keysService.onDidChange(() => this._onDidChange.fire()));
	}

	/**
	 * Ключи, пригодные для чата. Ключ показывается, пока проверка явно не забраковала его:
	 * непроверенный ключ тоже должен быть виден в списке моделей, иначе после добавления
	 * ключа в чате не появляется ничего.
	 */
	private usableKeys(): IAuraApiKey[] {
		return this.keysService.getKeys().filter(key => {
			const status = this.keysService.getStatus(key.id);
			if (status.ok === false) {
				return false;
			}
			return status.health !== 'unauthorized' && status.health !== 'forbidden';
		});
	}

	async provideLanguageModelChatInfo(_options: ILanguageModelChatInfoOptions, _token: CancellationToken): Promise<ILanguageModelChatMetadataAndIdentifier[]> {
		return this.usableKeys().map(key => {
			const status = this.keysService.getStatus(key.id);
			const metadata: ILanguageModelChatMetadata = {
				extension: new ExtensionIdentifier('aura.aura-api'),
				name: `${key.name} (${key.model})`,
				id: key.id,
				vendor: AURA_API_VENDOR,
				version: '1.0.0',
				family: key.model,
				maxInputTokens: 128000,
				maxOutputTokens: 16000,
				isDefaultForLocation: {},
				isUserSelectable: true,
				isBYOK: true,
				detail: key.group,
				tooltip: status.excludedHighPing
					? `Aura API: ${key.model} @ ${key.baseUrl} — высокий пинг (${status.pingMs} мс)`
					: `Aura API: ${key.model} @ ${key.baseUrl}`,
				capabilities: { toolCalling: true, agentMode: true },
			};
			return { identifier: toAuraModelIdentifier(key.id), metadata };
		});
	}

	/**
	 * Порядок перебора ключей: выбранная пользователем модель первой, затем остальные
	 * пригодные ключи как резерв (фейловер возможен только до первого байта ответа).
	 */
	private candidatesFor(modelIdentifier: string): IAuraApiKey[] {
		const keyId = toKeyId(modelIdentifier);
		const usable = this.usableKeys();
		const preferred = usable.find(k => k.id === keyId)
			?? this.keysService.getKeys().find(k => k.id === keyId)
			?? this.keysService.resolveKeyForModel?.()
			?? usable[0];
		if (!preferred) {
			return [];
		}
		return [preferred, ...usable.filter(k => k.id !== preferred.id)];
	}

	private buildMessages(messages: IChatMessage[]): IOpenAIMessage[] {
		const systemPrompt = (this.configurationService.getValue<string>(AURA_API_SYSTEM_PROMPT_SETTING) ?? '').trim();
		const result: IOpenAIMessage[] = [];
		if (systemPrompt) {
			result.push({ role: 'system', content: systemPrompt });
		}

		for (const message of messages) {
			const role = message.role === ChatMessageRole.System
				? 'system'
				: message.role === ChatMessageRole.User ? 'user' : 'assistant';

			const textChunks: string[] = [];
			const toolCalls: IOpenAIToolCall[] = [];

			for (const part of message.content) {
				if (part.type === 'text') {
					if (part.value) {
						textChunks.push(part.value);
					}
				} else if (part.type === 'tool_use') {
					toolCalls.push({
						id: part.toolCallId,
						type: 'function',
						function: { name: part.name, arguments: JSON.stringify(part.parameters ?? {}) },
					});
				} else if (part.type === 'tool_result') {
					// Результат инструмента — отдельное сообщение роли `tool`, привязанное к вызову.
					result.push({ role: 'tool', tool_call_id: part.toolCallId, content: partsToText(part.value) });
				}
			}

			if (textChunks.length === 0 && toolCalls.length === 0) {
				continue;
			}
			result.push({
				role,
				content: textChunks.join('\n'),
				...(toolCalls.length ? { tool_calls: toolCalls } : {}),
			});
		}

		return result;
	}

	private static toOpenAITools(options: ILanguageModelChatRequestOptions): unknown[] | undefined {
		const tools = (options as { tools?: readonly IChatRequestTool[] }).tools;
		if (!tools?.length) {
			return undefined;
		}
		return tools.map(tool => ({
			type: 'function',
			function: {
				name: tool.name,
				description: tool.description ?? '',
				parameters: tool.inputSchema ?? { type: 'object', properties: {} },
			},
		}));
	}

	async sendChatRequest(modelId: string, messages: IChatMessage[], _from: ExtensionIdentifier | undefined, options: ILanguageModelChatRequestOptions, token: CancellationToken): Promise<ILanguageModelChatResponse> {
		const candidates = this.candidatesFor(modelId);
		if (candidates.length === 0) {
			throw new Error('Aura API: нет доступных ключей. Добавьте ключ во вкладке «Aura API».');
		}

		const oaiMessages = this.buildMessages(messages);
		const tools = AuraApiChatProvider.toOpenAITools(options);

		const controller = new AbortController();

		let resolveResult!: (value: string) => void;
		let rejectResult!: (error: unknown) => void;
		const result = new Promise<string>((res, rej) => { resolveResult = res; rejectResult = rej; });
		// Потребители, читающие только поток, никогда не ждут `result`; без этого его отклонение
		// всплывает как unhandled rejection.
		result.catch(() => { });

		const stream = this.createStream(candidates, oaiMessages, tools, controller, token, resolveResult, rejectResult);
		return { stream, result };
	}

	private async *createStream(
		candidates: IAuraApiKey[],
		oaiMessages: IOpenAIMessage[],
		tools: unknown[] | undefined,
		controller: AbortController,
		token: CancellationToken,
		resolveResult: (value: string) => void,
		rejectResult: (error: unknown) => void,
	): AsyncIterable<IChatResponsePart> {
		let lastError: unknown;
		// После первого выданного куска фейловер невозможен — иначе текст задвоится.
		let yielded = false;
		// Отмену отслеживаем опросом на границах чанков, а не подпиской на токен:
		// подписка создаёт IDisposable, который некому освободить, если потребитель
		// не дочитает поток до конца — трекер утечек помечает его как LEAKED DISPOSABLE.
		const checkCancelled = () => {
			if (token.isCancellationRequested) {
				controller.abort();
			}
		};
		try {
			for (const key of candidates) {
				checkCancelled();
				if (controller.signal.aborted) {
					throw canceled();
				}
				try {
					yield* this.streamFromKey(key, oaiMessages, tools, controller, checkCancelled, () => { yielded = true; }, resolveResult);
					return;
				} catch (error) {
					if (controller.signal.aborted) {
						const cancellation = canceled();
						rejectResult(cancellation);
						throw cancellation;
					}
					if (yielded) {
						rejectResult(error);
						throw error;
					}
					this.logService.warn(`[AuraAPI] ключ «${key.name}» недоступен, пробуем следующий`, error);
					lastError = error;
				}
			}
			const error = lastError instanceof Error ? lastError : new Error('Aura API: все ключи недоступны');
			rejectResult(error);
			throw error;
		} finally {
			controller.abort(); // закрывает соединение, если потребитель бросил поток на середине
		}
	}

	private async *streamFromKey(
		key: IAuraApiKey,
		oaiMessages: IOpenAIMessage[],
		tools: unknown[] | undefined,
		controller: AbortController,
		checkCancelled: () => void,
		onYield: () => void,
		resolveResult: (value: string) => void,
	): AsyncIterable<IChatResponsePart> {
		const base = key.baseUrl.replace(/\/+$/, '');
		if (isBlockedByContentSecurityPolicy(base)) {
			throw new Error(`Aura API [${key.name}]: адрес ${base} использует http:// — политика безопасности окна разрешает только https:// (или localhost). Укажите https-адрес.`);
		}

		const secret = await this.keysService.getSecret(key.id);
		const response = await fetch(`${base}/chat/completions`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(secret ? { 'Authorization': `Bearer ${secret}` } : {}),
			},
			body: JSON.stringify({
				model: key.model,
				messages: oaiMessages,
				stream: true,
				...(tools ? { tools, tool_choice: 'auto' } : {}),
			}),
			signal: controller.signal,
		});

		if (!response.ok) {
			const body = await response.text().catch(() => '');
			throw new Error(`Aura API [${key.name}]: HTTP ${response.status} — ${body.slice(0, 200)}`);
		}
		if (!response.body) {
			// Эндпоинт проигнорировал stream:true и вернул цельный JSON.
			const body = await response.text();
			const text = this.textFromNonStreamedBody(body);
			if (text) {
				onYield();
				yield { type: 'text', value: text };
			}
			resolveResult(text);
			return;
		}

		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		const toolCalls = new Map<number, IToolCallAccumulator>();
		let buffer = '';
		let fullText = '';

		for (; ;) {
			checkCancelled();
			const { done, value } = await reader.read();
			if (done) {
				break;
			}
			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split('\n');
			buffer = lines.pop() ?? '';
			for (const line of lines) {
				const trimmed = line.trim();
				if (!trimmed.startsWith('data:')) {
					continue;
				}
				const payload = trimmed.slice(5).trim();
				if (!payload || payload === '[DONE]') {
					continue;
				}
				let json: {
					choices?: Array<{
						delta?: {
							content?: unknown;
							reasoning_content?: unknown;
							tool_calls?: Array<{ index?: number; id?: string; function?: { name?: string; arguments?: string } }>;
						};
					}>;
					error?: { message?: string };
				};
				try {
					json = JSON.parse(payload);
				} catch {
					continue; // неполный JSON-чанк
				}
				if (json.error?.message) {
					throw new Error(`Aura API [${key.name}]: ${json.error.message}`);
				}
				const delta = json.choices?.[0]?.delta;
				if (!delta) {
					continue;
				}
				if (typeof delta.reasoning_content === 'string' && delta.reasoning_content) {
					onYield();
					yield { type: 'thinking', value: delta.reasoning_content };
				}
				if (typeof delta.content === 'string' && delta.content) {
					fullText += delta.content;
					onYield();
					yield { type: 'text', value: delta.content };
				}
				for (const call of delta.tool_calls ?? []) {
					const index = call.index ?? 0;
					const acc = toolCalls.get(index) ?? { id: '', name: '', arguments: '' };
					if (call.id) { acc.id = call.id; }
					if (call.function?.name) { acc.name = call.function.name; }
					if (call.function?.arguments) { acc.arguments += call.function.arguments; }
					toolCalls.set(index, acc);
				}
			}
		}

		for (const call of toolCalls.values()) {
			if (!call.name) {
				continue;
			}
			let parameters: unknown = {};
			try {
				parameters = call.arguments ? JSON.parse(call.arguments) : {};
			} catch {
				this.logService.warn(`[AuraAPI] инструмент ${call.name}: аргументы не разобрались как JSON`);
			}
			onYield();
			yield { type: 'tool_use', name: call.name, toolCallId: call.id || `${call.name}-${toolCalls.size}`, parameters };
		}

		resolveResult(fullText);
	}

	private textFromNonStreamedBody(body: string): string {
		try {
			const parsed = JSON.parse(body);
			return String(parsed?.choices?.[0]?.message?.content ?? '');
		} catch {
			return body;
		}
	}

	async provideTokenCount(_modelId: string, message: string | IChatMessage, _token: CancellationToken): Promise<number> {
		const text = typeof message === 'string'
			? message
			: partsToText(message.content);
		return Math.ceil(text.length / 4); // приблизительная оценка токенов
	}
}
