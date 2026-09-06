/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { Disposable } from '../../../../../base/common/lifecycle.js';
import { AgentHostAgggAgentEnabledConfigKey, platformRootSchema } from '../../../common/agentHostSchema.js';
import type { IAgentHostChatContribution, IAgentHostChatContributionContext, ISendContribution } from '../../../common/agentHostChatContributionsService.js';
import { IAgentConfigurationService } from '../../agentConfigurationService.js';

export const AGGG_AGENT_INSTRUCTION = [
	'<aggg-agent-mode>',
	'AGGG2.0 global agent mode is enabled. Treat the bundled AGGG instructions, canon documents, and skills as the operating guide for this turn.',
	'Use the installed AGGG tools only when they are available and appropriate. Never invent research, tool results, measurements, or verification.',
	'Before executing downloaded code, system changes, network installation, or destructive operations, explain the impact and obtain explicit user approval.',
	'Never expose credentials, tokens, private source code, personal data, or private AGGG files in reports or external services.',
	'If AGGG itself fails, prepare a sanitized developer bug-report draft with reproduction steps, expected and actual behavior, relevant logs, Aura IDE version, operating system, and AGGG version. Ask the user to review it before sending.',
	'</aggg-agent-mode>',
].join('\n');

/** Adds the global AGGG instruction to every enabled Agent Host turn. */
export class AgggAgentContribution extends Disposable implements IAgentHostChatContribution {

	static readonly id = 'agggAgent';
	readonly order = 50;

	constructor(
		protected readonly _context: IAgentHostChatContributionContext,
		@IAgentConfigurationService private readonly _agentConfigService: IAgentConfigurationService,
	) {
		super();
	}

	onOutgoingTurn(): ISendContribution | undefined {
		return this._agentConfigService.getRootValue(platformRootSchema, AgentHostAgggAgentEnabledConfigKey)
			? { instructions: [AGGG_AGENT_INSTRUCTION] }
			: undefined;
	}
}
