/** @odoo-module */
import { ChatWindow } from "@mail/core/common/chat_window";
import { patch } from "@web/core/utils/patch";
import { jsonrpc } from "@web/core/network/rpc_service";
import { onMounted } from "@odoo/owl";
import { useState } from "@odoo/owl";
import { useRef } from "@odoo/owl";

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.contentRef = useRef("content");
        onMounted(async () => {
            var self = this;
            if (this.actionService?.currentController?.action && this.actionService.currentController.action.name === 'Discuss Whatsapp') {
                await jsonrpc('/select_colors', {}).then(function(result) {
                if (self.contentRef?.el) {
                if (result.background_color !== false){
                    self.contentRef.el.style.setProperty("--background-color",result.background_color
                    );
                    }
                if (result.chat_interface_background !== false){
                    self.contentRef.el.style.setProperty("background-image",'url(data:image/png;base64,'+result.chat_interface_background+')',"important");
                }
                }
            });
            }
        });
    },
});