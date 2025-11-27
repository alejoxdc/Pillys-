/** @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { onWillDestroy, useEffect } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup();
        useEffect(
            () => {
                this.checkComposerDisabled();
            },
            () => [this.thread?.attention_state]
        );
        // onWillDestroy(() => clearTimeout(this.composerDisableCheckTimeout));
    },

    get placeholder() {
        if (
            this.thread &&
            this.thread.type === "whatsapp" &&
            !this.thread.attention_state
        ) {
            return _t(
                "Can't send message until you hit the in attention button."
            );
        }
        return super.placeholder;
    },

    checkComposerDisabled() {
        if (this.thread && this.thread.type === "whatsapp") {
            if (!this.thread.attention_state) {
                this.state.active = false;
            } else {
                this.state.active = true;
                this.props.composer.threadExpired = false;
            }
        }
    },

    /** @override */
    get isSendButtonDisabled() {
        const whatsappInactive = (this.thread && this.thread.type == 'whatsapp' && !this.state.active && !this.thread.attention_state);
        return super.isSendButtonDisabled || whatsappInactive;
    },
});
