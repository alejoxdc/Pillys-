/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { DiscussSidebar } from "@mail/core/web/discuss_sidebar";
import { DiscussSidebarMailboxes } from "@mail/core/web/discuss_sidebar_mailboxes";
import { DiscussSidebarStartMeeting } from "@mail/discuss/call/web/discuss_sidebar_start_meeting";
import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { onMounted, onWillStart, useRef } from "@odoo/owl";
import { useState } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";

patch(DiscussSidebar.prototype, {
    setup() {
        super.setup();
        this.hideWhatsappMenu = 'false';
        this._whatsappMenuHide();
        onMounted(async () => {
            const whatsappMenuHide = await jsonrpc('/hide_whatsapp_menu', {});
            if (whatsappMenuHide.whatsapp_hide) {
                this.hideWhatsappMenu = 'true';
                if (this.__owl__.parent.component.__owl__.parent.parent.props.action.name === 'Discuss') {
                    const whatsappCategory = document.querySelector('.o-mail-DiscussSidebarCategory-whatsapp');
                    if (whatsappCategory) {
                        whatsappCategory.style.setProperty('display', 'none', 'important');
                    }
                }
                this.render();
            }
        });
    },
});