/* @odoo-module */
import { Component, useState, onMounted} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { jsonrpc } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";


export class TopButtons extends Component {

     setup(){
        this.actionService = useService('action');
        this.action_id = false;
        var self = this
     }
     on_click() {
          jsonrpc('/web/dataset/call_kw/discuss.channel/action_whatsapp',{ model: 'discuss.channel', method: 'action_whatsapp',
                      args: [0],
                      kwargs: {}
                     }).then(function(values){
                     if(values){
                        self.action_id = values
                     }
                     });
                     setTimeout(() => {
                         if (self.action_id){
                                this.actionService.doAction({
                                type: "ir.actions.client",
                                tag: "mail.action_discuss",
                                id: self.action_id,
                                name: _t("Discuss Whatsapp"),
                                });
                         }
                         else{
                                this.actionService.doAction({
                                type: "ir.actions.client",
                                tag: "mail.action_discuss",
                                name: _t("Discuss Whatsapp"),
                                });
                         }
                    }, 20);

     }

}
TopButtons.template = "odx_odoo_whatsapp_interface.ActivityMenus";
export const systrayItem = {
    Component: TopButtons,
};
registry.category("systray").add("TopButton", systrayItem, { sequence: 40 });