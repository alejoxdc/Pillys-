 /** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { useState } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";

patch(Message.prototype, {
    setup() {
            super.setup(...arguments);
            this.discuss_name = _t("Discuss");
            this.is_whatsapp = false;
            if (!this.props.message.whatsappStatus){
                this._fetchWhatsappMessageType();
            }

            if(this.props.thread){

                if(this.props.thread.type === 'whatsapp'){
                    this.is_whatsapp = true;
                }
            }
            else if(this.__owl__.parent.parent.props.message){
                if (this.__owl__.parent.parent.props.message.type === 'whatsapp_message'){
                        this.is_whatsapp = true;
                }
            }
        },

    async _fetchWhatsappMessageType() {
        if (this.props.message.id) {
           try {
                      const result = await jsonrpc('/send_whatsappMessageType', {
                      message_id: this.props.message.id,
                });
                if (result && result.whatsappMessageType) {
                        this.props.message.whatsappMessageType = result.whatsappMessageType
                }

            } catch (error) {
                console.error('Failed to fetch WhatsApp message type:', error);
            }
        }
    },
});

