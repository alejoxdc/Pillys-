/** @odoo-module */
import { Discuss } from "@mail/core/common/discuss";
import { patch} from "@web/core/utils/patch";
import { jsonrpc } from "@web/core/network/rpc_service";
const { useRef } = owl;
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(Discuss.prototype, {
    setup() {
     super.setup(...arguments);
        this.core = useRef("core");
        this.actionService = useService('action');
        onMounted(async () => {
            var self = this;
            if (this.__owl__.parent.props.action.name === 'Discuss Whatsapp') {
                await jsonrpc('/select_colors', {}).then(function(result) {
                if (result.background_color !== false){
                    self.core.el.style.setProperty("--background-color",result.background_color
                    );
                    }
                if (result.chat_interface_background !== false){
                    self.core.el.style.setProperty("background-image",'url(data:image/png;base64,'+result.chat_interface_background+')',"important");
                }
                setTimeout(() => {
                        const whatsappCurrentUsersHeaders = document.querySelectorAll('.o-mail-Discuss-header');
                        whatsappCurrentUsersHeaders.forEach((whatsappCurrentUsersHeader) => {
                            whatsappCurrentUsersHeader.classList.remove('bg-view');
                            whatsappCurrentUsersHeader.classList.add('cust-bg-view');
                            const whatsappThreadNames = whatsappCurrentUsersHeader.querySelectorAll('.o-mail-Discuss-threadName');
                                whatsappThreadNames.forEach((threadname) => {
                                    threadname.classList.remove('text-dark');
                                    threadname.classList.add('cust-text-white');
                            });
                        });
                    }, 20);
            });
            }
        });
    },
    openPartnerPopup() {
        const partnerId = this.thread.whatsapp_partner_id;
        if (partnerId) {
             this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                res_id: parseInt(partnerId),
                views: [[false, 'form']],
                target: 'new',
            });
        }
    },
});

