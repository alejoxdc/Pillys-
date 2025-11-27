/* @odoo-module */
import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
const expandDiscussAction = threadActionsRegistry.get("expand-discuss");

patch(expandDiscussAction,  {
    condition(component) {
        return (
            component.thread &&
            component.props.chatWindow?.isOpen &&
            component.thread.model === "discuss.channel" &&
            !component.ui.isSmall
        );
    },
    icon: "fa fa-fw fa-expand",
    name: _t("Open in Discuss"),
    open(component) {
        component.threadService.setDiscussThread(component.thread);
        if (component.thread.type === "whatsapp"){
        component.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
                id: component.thread.action_id_whatsapp,
                name: _t("Discuss Whatsapp"),

            },
            { clearBreadcrumbs: true }
        );
        }
        else {
        component.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
                name: _t("Discuss"),
            },
            { clearBreadcrumbs: true }
        );
        }
    },
    sequence: 15,
});

