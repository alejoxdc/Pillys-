/* @odoo-module */
import { Thread } from "@mail/core/common/thread_model";
import { assignDefined, assignIn } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { toRaw } from "@odoo/owl";


patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if (this.type === "whatsapp") {
            assignDefined(this, data, ["whatsapp_partner_id"]);
            assignDefined(this, data, ["whatsapp_partner_name"]);
            assignDefined(this, data, ["whatsapp_partner_img_url"]);
            assignDefined(this, data, ["action_id_whatsapp"]);
            if (!this._store.discuss.whatsapp.threads.includes(this)) {
                this._store.discuss.whatsapp.threads.push(this);
            }
        }

    }
});