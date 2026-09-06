/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { promises as fs } from 'fs';
import { spawn } from 'child_process';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';

const CONFIGURATION_SECTION = 'aggg.agent';
const ENABLED_SETTING = 'enabled';
const TOGGLE_COMMAND = 'aggg.agent.toggle';
const INSTALL_COMMAND = 'aggg.agent.install';
const SYSTEM_SETUP_COMMAND = 'aggg.agent.runSystemSetup';
const BUG_REPORT_COMMAND = 'aggg.agent.createBugReport';
const INSTALL_STATE_KEY = 'installedVersion';
const CHECK_TIMEOUT_MS = 2 * 60 * 1000;
const SETUP_TIMEOUT_MS = 30 * 60 * 1000;

interface PythonCommand {
	readonly executable: string;
	readonly prefixArguments: readonly string[];
}

interface BundleDeployment {
	commit(): Promise<void>;
	rollback(): Promise<void>;
}

let outputChannel: vscode.OutputChannel;
let statusItem: vscode.StatusBarItem;
let installPromise: Promise<void> | undefined;
let sanitizedLog = '';

export function activate(context: vscode.ExtensionContext): void {
	outputChannel = vscode.window.createOutputChannel(vscode.l10n.t('AGGG Agent'));
	statusItem = vscode.window.createStatusBarItem('status.aggg.agent', vscode.StatusBarAlignment.Left, 90);
	statusItem.name = vscode.l10n.t('AGGG Agent');
	statusItem.command = TOGGLE_COMMAND;

	context.subscriptions.push(
		outputChannel,
		statusItem,
		vscode.commands.registerCommand(TOGGLE_COMMAND, () => toggle(context)),
		vscode.commands.registerCommand(INSTALL_COMMAND, () => install(context, true)),
		vscode.commands.registerCommand(SYSTEM_SETUP_COMMAND, () => runSystemSetup(context)),
		vscode.commands.registerCommand(BUG_REPORT_COMMAND, () => createBugReport(context)),
		vscode.workspace.onDidChangeConfiguration(event => {
			if (event.affectsConfiguration(`${CONFIGURATION_SECTION}.${ENABLED_SETTING}`)) {
				updateStatusItem();
				if (isEnabled()) {
					void install(context, false).catch(() => undefined);
				}
			}
		}),
	);

	updateStatusItem();
	if (isEnabled()) {
		void install(context, false).catch(() => undefined);
	}
}

function isEnabled(): boolean {
	return vscode.workspace.getConfiguration(CONFIGURATION_SECTION).get<boolean>(ENABLED_SETTING, false);
}

function updateStatusItem(): void {
	const enabled = isEnabled();
	statusItem.text = enabled ? '$(shield) AGGG: On' : '$(shield) AGGG: Off';
	statusItem.tooltip = enabled
		? vscode.l10n.t('AGGG instructions are active globally for every chat model. Click to disable.')
		: vscode.l10n.t('AGGG instructions are disabled. Click to install and enable globally.');
	statusItem.show();
}

async function toggle(context: vscode.ExtensionContext): Promise<void> {
	const nextEnabled = !isEnabled();
	if (nextEnabled) {
		try {
			await install(context, false);
		} catch {
			return;
		}
	}

	await vscode.workspace.getConfiguration(CONFIGURATION_SECTION).update(
		ENABLED_SETTING,
		nextEnabled,
		vscode.ConfigurationTarget.Global,
	);
	void vscode.window.showInformationMessage(nextEnabled
		? vscode.l10n.t('AGGG Agent is enabled globally for all chat models.')
		: vscode.l10n.t('AGGG Agent is disabled.'));
}

async function install(context: vscode.ExtensionContext, force: boolean): Promise<void> {
	if (installPromise) {
		return installPromise;
	}

	installPromise = installImpl(context, force).finally(() => {
		installPromise = undefined;
	});
	return installPromise;
}

async function installImpl(context: vscode.ExtensionContext, force: boolean): Promise<void> {
	const sourceRoot = path.join(context.extensionPath, 'resources', 'aggg2');
	const targetRoot = path.join(context.globalStorageUri.fsPath, 'aggg2');
	const version = (await fs.readFile(path.join(sourceRoot, 'VERSION'), 'utf8')).trim();
	const deployedVersion = await readVersion(path.join(targetRoot, 'VERSION'));
	if (!force && context.globalState.get<string>(INSTALL_STATE_KEY) === version && deployedVersion === version) {
		return;
	}

	await vscode.window.withProgress({
		location: vscode.ProgressLocation.Notification,
		title: vscode.l10n.t('Installing AGGG Agent {0}', version),
		cancellable: true,
	}, async (_progress, token) => {
		outputChannel.clear();
		sanitizedLog = '';
		outputChannel.show(true);
		appendLog(vscode.l10n.t('Deploying the bundled agent to {0}', targetRoot));
		const deployment = await deployBundle(sourceRoot, targetRoot, token);

		try {
			await runSetup(targetRoot, token, true);
		} catch (error) {
			try {
				await deployment.rollback();
			} catch (rollbackError) {
				appendLog(vscode.l10n.t('Failed to restore the previous installation: {0}', rollbackError instanceof Error ? rollbackError.message : String(rollbackError)));
			}
			const message = error instanceof Error ? error.message : String(error);
			appendLog(vscode.l10n.t('Installation failed: {0}', message));
			await createBugReport(context, message);
			void vscode.window.showErrorMessage(vscode.l10n.t('AGGG Agent installation failed. A bug report draft was opened.'));
			throw error;
		}

		await context.globalState.update(INSTALL_STATE_KEY, version);
		await deployment.commit();
		appendLog(vscode.l10n.t('AGGG Agent deployment and setup validation completed.'));
		void vscode.window.showInformationMessage(vscode.l10n.t('AGGG Agent {0} is installed.', version));
	});
}

async function deployBundle(sourceRoot: string, targetRoot: string, token: vscode.CancellationToken): Promise<BundleDeployment> {
	const temporaryRoot = `${targetRoot}.installing`;
	const backupRoot = `${targetRoot}.previous`;
	await fs.mkdir(path.dirname(targetRoot), { recursive: true });
	await fs.rm(temporaryRoot, { recursive: true, force: true });
	await fs.rm(backupRoot, { recursive: true, force: true });
	await fs.cp(sourceRoot, temporaryRoot, { recursive: true });
	if (token.isCancellationRequested) {
		await fs.rm(temporaryRoot, { recursive: true, force: true });
		throw new Error(vscode.l10n.t('Installation was cancelled.'));
	}

	let hadPreviousInstallation = false;
	try {
		await fs.rename(targetRoot, backupRoot);
		hadPreviousInstallation = true;
	} catch (error) {
		if (!isFileNotFoundError(error)) {
			throw error;
		}
	}

	try {
		await fs.rename(temporaryRoot, targetRoot);
	} catch (error) {
		if (hadPreviousInstallation) {
			await fs.rename(backupRoot, targetRoot);
		}
		throw error;
	}

	return {
		commit: () => fs.rm(backupRoot, { recursive: true, force: true }),
		rollback: async () => {
			await fs.rm(targetRoot, { recursive: true, force: true });
			if (hadPreviousInstallation) {
				await fs.rename(backupRoot, targetRoot);
			}
		},
	};
}

function isFileNotFoundError(error: unknown): error is NodeJS.ErrnoException {
	return error instanceof Error && 'code' in error && error.code === 'ENOENT';
}

async function runSystemSetup(context: vscode.ExtensionContext): Promise<void> {
	const proceed = await vscode.window.showWarningMessage(
		vscode.l10n.t('AGGG system setup can download dependencies and modify user-level shell, agent, MCP, Git hook, and tool configuration. It runs only the reviewed setup entry point; external harnesses and unrelated scripts are not run automatically. Continue?'),
		{ modal: true },
		vscode.l10n.t('Run Setup'),
	);
	if (!proceed) {
		return;
	}

	await install(context, false);
	const targetRoot = path.join(context.globalStorageUri.fsPath, 'aggg2');
	await vscode.window.withProgress({
		location: vscode.ProgressLocation.Notification,
		title: vscode.l10n.t('Running AGGG System Setup'),
		cancellable: true,
	}, async (_progress, token) => {
		try {
			await runSetup(targetRoot, token, false);
			void vscode.window.showInformationMessage(vscode.l10n.t('AGGG system setup completed.'));
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error);
			await createBugReport(context, message);
			void vscode.window.showErrorMessage(vscode.l10n.t('AGGG system setup failed. A bug report draft was opened.'));
		}
	});
}

async function runSetup(targetRoot: string, token: vscode.CancellationToken, checkOnly: boolean): Promise<void> {
	const commands: readonly PythonCommand[] = process.platform === 'win32'
		? [
			{ executable: 'py', prefixArguments: ['-3'] },
			{ executable: 'python', prefixArguments: [] },
			{ executable: 'python3', prefixArguments: [] },
		]
		: [
			{ executable: 'python3', prefixArguments: [] },
			{ executable: 'python', prefixArguments: [] },
		];

	let lastError: Error | undefined;
	for (const command of commands) {
		try {
			await runProcess(command, targetRoot, token, checkOnly);
			return;
		} catch (error) {
			lastError = error instanceof Error ? error : new Error(String(error));
			if (!lastError.message.includes('ENOENT')) {
				throw lastError;
			}
		}
	}

	throw lastError ?? new Error(vscode.l10n.t('Python 3 was not found.'));
}

function runProcess(command: PythonCommand, targetRoot: string, token: vscode.CancellationToken, checkOnly: boolean): Promise<void> {
	return new Promise((resolve, reject) => {
		const child = spawn(command.executable, [
			...command.prefixArguments,
			path.join('scripts', 'setup.py'),
			...(checkOnly ? ['--check'] : []),
		], {
			cwd: targetRoot,
			env: { ...process.env, PYTHONUTF8: '1' },
			windowsHide: true,
		});

		child.stdout.on('data', (chunk: Buffer) => appendLog(chunk.toString('utf8'), false));
		child.stderr.on('data', (chunk: Buffer) => appendLog(chunk.toString('utf8'), false));
		const timeout = setTimeout(() => child.kill(), checkOnly ? CHECK_TIMEOUT_MS : SETUP_TIMEOUT_MS);
		const cancellation = token.onCancellationRequested(() => child.kill());
		let settled = false;
		const finish = (error?: Error) => {
			if (settled) {
				return;
			}
			settled = true;
			clearTimeout(timeout);
			cancellation.dispose();
			error ? reject(error) : resolve();
		};

		child.once('error', error => {
			finish(error);
		});
		child.once('exit', (code, signal) => {
			if (token.isCancellationRequested) {
				finish(new Error(vscode.l10n.t('Installation was cancelled.')));
			} else if (signal) {
				finish(new Error(vscode.l10n.t('Setup timed out and was stopped.')));
			} else if (code === 0) {
				finish();
			} else {
				finish(new Error(vscode.l10n.t('Setup exited with code {0}.', code ?? -1)));
			}
		});
	});
}

async function createBugReport(context: vscode.ExtensionContext, failure?: string): Promise<void> {
	const bundledVersion = await readVersion(path.join(context.extensionPath, 'resources', 'aggg2', 'VERSION'));
	const installedVersion = await readVersion(path.join(context.globalStorageUri.fsPath, 'aggg2', 'VERSION'));
	const report = [
		'# AGGG Agent Bug Report',
		'',
		'## Summary',
		failure ? sanitizeForReport(failure) : '<Describe what went wrong>',
		'',
		'## Steps to Reproduce',
		'1. ',
		'2. ',
		'',
		'## Environment',
		`- Aura IDE: ${vscode.version}`,
		`- OS: ${os.type()} ${os.release()} (${os.arch()})`,
		`- Bundled AGGG: ${bundledVersion}`,
		`- Installed AGGG: ${installedVersion}`,
		`- Global mode: ${isEnabled() ? 'enabled' : 'disabled'}`,
		'',
		'## Expected Behavior',
		'',
		'## Actual Behavior',
		'',
		'## Recent Sanitized Setup Log',
		'```text',
		sanitizedLog || '<No setup log captured>',
		'```',
		'',
		'> Review this draft for private data before sending it to the AGGG developer.',
	].join('\n');
	const document = await vscode.workspace.openTextDocument({ language: 'markdown', content: report });
	await vscode.window.showTextDocument(document, { preview: false });
}

function appendLog(value: string, line = true): void {
	const rendered = line ? `${value}\n` : value;
	outputChannel.append(rendered);
	const redacted = sanitizeForReport(rendered);
	sanitizedLog = `${sanitizedLog}${redacted}`.slice(-32_000);
}

function sanitizeForReport(value: string): string {
	let sanitized = value;
	const privatePaths = [os.homedir(), ...(vscode.workspace.workspaceFolders?.map(folder => folder.uri.fsPath) ?? [])];
	for (const privatePath of privatePaths) {
		if (privatePath) {
			sanitized = sanitized.replace(new RegExp(escapeRegExp(privatePath), 'gi'), '<private-path>');
		}
	}
	return sanitized
		.replace(/(authorization\s*:\s*(?:bearer|basic)\s+)\S+/gi, '$1<redacted>')
		.replace(/((?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret|cookie)\s*[=:]\s*["']?)[^\s,"'}]+/gi, '$1<redacted>')
		.replace(/(--(?:api[_-]?key|token|password|secret)(?:=|\s+))\S+/gi, '$1<redacted>')
		.replace(/([?&](?:api[_-]?key|token|password|secret)=)[^&#\s]+/gi, '$1<redacted>')
		.replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '<private-email>')
		.replace(/\b(?:[A-F0-9]{40,}|[A-Za-z0-9_-]{48,})\b/g, '<redacted-value>');
}

function escapeRegExp(value: string): string {
	return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function readVersion(filename: string): Promise<string> {
	try {
		return (await fs.readFile(filename, 'utf8')).trim();
	} catch {
		return 'not installed';
	}
}
