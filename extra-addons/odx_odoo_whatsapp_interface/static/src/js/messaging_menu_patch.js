/** @odoo-module */

import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { jsonrpc } from "@web/core/network/rpc_service";


patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.hideWhatsappMenu = 'false';
        this.discuss_name = _t("Discuss");
        this._whatsappMenuHide();
    },
    async _whatsappMenuHide() {
            const whatsappMenuHide = await jsonrpc('/hide_whatsapp_menu', {});
            if (whatsappMenuHide.whatsapp_hide) {
                this.hideWhatsappMenu = 'true';
                this.render();
        }
    },
});