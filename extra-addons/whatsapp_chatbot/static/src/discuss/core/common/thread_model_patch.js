/** @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        assignDefined(this, data, ["activate_bot", "whatsapp_partner_id", "partner_category_id", "current_opportunity_id", "attention_state", "last_message_trucated", "recently_terminated"]);
        super.update(data);
    },
});
