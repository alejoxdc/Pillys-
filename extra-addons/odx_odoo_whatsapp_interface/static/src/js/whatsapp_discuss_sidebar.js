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
import { DiscussSidebarCategories } from "@mail/discuss/core/web/discuss_sidebar_categories";
import { markEventHandled } from "@web/core/utils/misc";
import { _t } from "@web/core/l10n/translation";



patch(DiscussSidebarCategories.prototype, {
setup() {
        super.setup();
        this.hideWhatsappMenu = 'false';
        this.discuss_name = _t("Discuss");
        this.root = useRef("root")
        this.state = useState({ sidebar: 'channels' , chat:'chats'});
        onMounted(() => {
                    if (this.__owl__.parent.component.__owl__.parent.parent.props.action.name === 'Discuss Whatsapp') {
                        const whatsappCategory = document.querySelector('.o-mail-DiscussSidebarCategory-whatsapp');
                        if (whatsappCategory) {
                            whatsappCategory.classList.add('cust-my-1');
                            const categoryNameDiv = whatsappCategory.querySelector('.d-flex');
                            if (categoryNameDiv) {
                                categoryNameDiv.classList.add('cust-text-white');
                            }
                            const searchWaChannelDiv = whatsappCategory.querySelector('.me-3');
                            if (searchWaChannelDiv) {
                                const searchWaPlusBtnDiv = whatsappCategory.querySelector('.o-mail-DiscussSidebarCategory-add');
                                if (searchWaPlusBtnDiv) {
                                    searchWaPlusBtnDiv.classList.add('cust-text-white');
                                }
                            }
                        }
                    }
                    this._whatsappMenuHide();
            });
        },
        async _whatsappMenuHide() {
            const whatsappMenuHide = await jsonrpc('/hide_whatsapp_menu', {});
            if (whatsappMenuHide.whatsapp_hide) {
                this.hideWhatsappMenu = 'true';
                this.render();
        }
    },
});
