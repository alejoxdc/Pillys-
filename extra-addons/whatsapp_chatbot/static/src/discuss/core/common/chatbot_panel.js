/* @odoo-module */

import { Component, onWillStart, onWillUpdateProps, useState, useRef } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { useSequential, useVisible } from "@mail/utils/common/hooks";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 *
 * @extends {Component<Props, Env>}
 */
export class ChatbotPanel extends Component {
    static components = { ActionPanel };
    static defaultProps = { channelActiveClass: true };
    static props = ["channelActiveClass?", "thread"];
    static template = "discuss.ChatbotPanel";

    setup() {
        this.sequential = useSequential();
        this.ormService = useService("orm");
        this.store = useState(useService("mail.store"));
        this.inputRef = useRef("input");
        this.inputRefQuick = useRef("inputQuick");
        this.ui = useService("ui");
        this.actionService = useService('action');

        this.searchStr = "";
        this.searchStrQuick = "";
        this.state = useState({
            sendableTemplates: [],
            quickResponses: [],
            opportunityStages: [],
            members: [],
            activateBot: this.props.thread.activate_bot,
            attentionState: this.props.thread.attention_state,
            opportunityStage: 0,
            choosenMember: 0,
        });
        onWillStart(async () => {
            if (this.store.user) {
                try {
                    await this.fetchTemplatesToSend();
                    await this.fetchOpportunityStage();
                    await this.fetchCrmStages();
                    await this.fetchQuickResponses();
                    await this.fetchMembers();
                } catch (error) {
                    console.error('Error during onWillStart:', error);
                }
            }
        });
        onWillUpdateProps(async (nextProps) => {
            if (nextProps.thread.notEq(this.props.thread)) {
                this.state.activateBot = nextProps.thread.activate_bot;
                this.state.attentionState = nextProps.thread.attention_state;
                this.state.opportunityStage = nextProps.thread.current_opportunity_id;
                try {
                    await this.fetchTemplatesToSend();
                    await this.fetchOpportunityStage();
                    await this.fetchCrmStages();
                    await this.fetchQuickResponses();
                    await this.fetchMembers();
                } catch (error) {
                    console.error('Error during onWillUpdateProps:', error);
                }
            }
        });
    }

    updateActivateBot() {
        this.sequential(() =>
            this.ormService.write("discuss.channel", [this.props.thread.id], {
                activate_bot: !this.props.thread.activate_bot,
            })
        );
        this.state.activateBot = !this.state.activateBot;
    }

    updateAttentionState() {
        this.sequential(() =>
            this.ormService.write("discuss.channel", [this.props.thread.id], {
                attention_state: !this.props.thread.attention_state,
            })
        );
        this.state.attentionState = !this.state.attentionState;

        this.attentionStateFetched(this.props.thread, this.state.attentionState);
        let id = this.props.thread.id;
        const thread = this.store.Thread.get({ model: "discuss.channel", id });
        thread.update({ attention_state: this.state.attentionState });
        thread.update({ activate_bot: !this.state.attentionState });
        this.state.activateBot = !this.state.attentionState;
        this.ui.bus.trigger("update_attention_state");
    }

    async setConversationFree() {
        const newAttentionState = !this.props.thread.attention_state;
        await this.sequential(async () => {
            await this.ormService.write("discuss.channel", [this.props.thread.id], {
                attention_state: newAttentionState,
            });
            await this.ormService.call("discuss.channel", "set_conversation_free", [this.props.thread.id]);
        });
        this.state.attentionState = newAttentionState;
        const thread = this.store.Thread.get({ model: "discuss.channel", id: this.props.thread.id });
        thread.update({ attention_state: newAttentionState });
        this.ui.bus.trigger("update_attention_state");
    }

    async fetchTemplatesToSend() {
        const results = await this.sequential(() =>
            this.ormService.call("whatsapp.template", "search_for_templates_to_send", [
                this.props.thread.id,
                this.searchStr
            ])
        );
        if (!results) {
            return;
        }
        this.state.sendableTemplates = results;
    }

    async fetchQuickResponses() {
        const results = await this.sequential(() =>
            this.ormService.call("whatsapp.quick.response", "search_for_quick_response", [
                this.props.thread.id,
                this.searchStrQuick
            ])
        );
        if (!results) {
            return;
        }
        this.state.quickResponses = results;
    }
    async fetchMembers() {
        const results = await this.sequential(() =>
            this.ormService.call("discuss.channel", "get_channel_members_but_current", [
                this.props.thread.id
            ])
        );
        if (!results) {
            return;
        }
        this.state.members = results;
    }

    updateChoosenMember(event) {
        this.state.choosenMember = event.target.value;
    }

    onInput() {
        this.searchStr = this.inputRef.el.value;
        this.fetchTemplatesToSend();
    }

    onInputQuick() {
        this.searchStrQuick = this.inputRefQuick.el.value;
        this.fetchQuickResponses();
    }

    onClickSendTemplate(template) {
        this.sequential(async () => {
            await this.ormService.call("res.partner", "send_whatsapp_template_from_discuss", [this.props.thread.id, template.id, this.props.thread.id], {});
        });
    }

    onClickPasteQuickResponse(quickResponse) {
        // Find the quick response with the given ID
        if (quickResponse) {
            // Find the closest textarea with the class 'o-mail-Composer-input'
            const textarea = document.querySelector('.o-mail-Composer-input');

            if (textarea) {
                // Focus the textarea
                textarea.focus();

                // Get the current cursor position
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;

                // Insert the text at the cursor position
                let textBefore = textarea.value.substring(0, start);
                const textAfter = textarea.value.substring(end);
                if (textBefore && !textBefore.endsWith('\n')) {
                    textBefore += '\n\n';
                }
                textarea.value = textBefore + quickResponse.body + textAfter;

                // Move the cursor to the end of the inserted text
                const cursorPosition = start + quickResponse.body.length;
                textarea.setSelectionRange(cursorPosition, cursorPosition);

                // Trigger input event to notify any listeners
                const event = new Event('input', { bubbles: true });
                textarea.dispatchEvent(event);
            } else {
                console.error('Textarea with class "o-mail-Composer-input" not found.');
            }
        } else {
            console.error(`Quick response with ID ${quickResponse} not found.`);
        }
    }

    async attentionStateFetched(thread, attention_state) {
        this.sequential(async () => {
            await this.ormService.call("discuss.channel", "attention_state_fetched", [thread.id, attention_state], {});
        });
    }

    async delegateChannel() {
        if (!this.state.choosenMember) {
            return;
        }
        this.sequential(async () => {
            await this.ormService.call("discuss.channel", "delegate_channel", [this.props.thread.id, this.state.choosenMember], {});
        });
    }

    async updateOpportunityStage(event) {
        // Get the selected value from the event
        const selectedStageId = event.target.value;
        this.sequential(async () => {
            await this.ormService.call("discuss.channel", "update_opportunity_stage", [this.props.thread.id, selectedStageId], {})
        });
        this.state.opportunityStage = selectedStageId;
    }

    async fetchOpportunityStage() {
        const results = await this.sequential(() =>
            this.ormService.call("discuss.channel", "current_opportunity_stage", [
                this.props.thread.id
            ])
        );
        if (!results) {
            return;
        }
        this.state.opportunityStage = results;
    }

    async fetchCrmStages() {
        const results = await this.sequential(() =>
            this.ormService.call("crm.lead", "get_crm_stages", [
                this.props.thread.id
            ])
        );
        if (!results) {
            return;
        }
        this.state.opportunityStages = results;
    }

    openLeadPopup() {
        const leadId = this.props.thread.current_opportunity_id;
        if (leadId) {
             this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'crm.lead',
                res_id: parseInt(leadId),
                views: [[false, 'form']],
                target: 'new',
            });
        }
    }

    get title() {
        return _t("Chatbot");
    }

}