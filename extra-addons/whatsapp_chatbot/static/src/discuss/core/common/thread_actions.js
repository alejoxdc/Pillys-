/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { ChatbotPanel } from "@whatsapp_chatbot/discuss/core/common/chatbot_panel";
import { _t } from "@web/core/l10n/translation";

threadActionsRegistry.add("whatsapp-chatbot", {
    condition: (component) =>
        component.thread?.type === "whatsapp" &&
        (!component.props.chatWindow || component.props.chatWindow.isOpen),
        component: ChatbotPanel, // Replace this with the actual component for your action.
    panelOuterClass: "o-discuss-ChatbotPanel",
    icon: "fa fa-fw fa-flickr",
    iconLarge: "fa fa-fw fa-lg fa-flickr",
    name: _t("Show Chatbot Actions"), 
    nameActive: _t("Hide Chatbot Actions"),
    setup(action) {
        // This function is called when the action is being set up.
        // You can use this function to initialize any properties of the action.
    },
    open(component, action) {
        // This function is called when the action is opened.
        // You can use this function to control what happens when the action is opened.
    },
    close(component, action) {
        // This function is called when the action is closed.
        // You can use this function to control what happens when the action is closed.
    },
    name: "Chatbot Action", // Replace this with the actual name of your action.
    sequence: 10, // Replace this with the actual sequence number for your action.
    toggle: true, // Replace this with whether or not your action should be toggleable.
});