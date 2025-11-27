/* @odoo-module */

import { Component, onWillStart, onWillUpdateProps, useState, useRef } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { useSequential } from "@mail/utils/common/hooks";
import { _t } from "@web/core/l10n/translation";
import { DiscussSidebarCategories } from "@mail/discuss/core/web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";


patch(DiscussSidebarCategories.prototype, {
    setup() {
        super.setup(...arguments);
        this.isDestroyed = false;
        this.sequential = useSequential();
        this.ui = useService("ui");
        this.ormService = useService("orm");
        this.busService = this.env.services.bus_service
        this.channel = "attention_state_fetched"
        this.busService.addChannel(this.channel)
        this.busService.addEventListener("notification", this.updateAttentionState.bind(this))
    },
    componentWillUnmount() {
        this.isDestroyed = true;
    },
    async updateAttentionState({ detail: notifications }) {
        if (this.isDestroyed) return;
        if (!notifications || notifications.length === 0) {
            console.error("Invalid or empty notifications object:", notifications);
            return;
        }
        try {
            if (notifications[0].type === "notification") {
                const { channel_id, attention_state, recently_terminated } = notifications[0].payload;
                if (!channel_id || attention_state === undefined) {
                    return;
                }
                const thread = this.store.Thread.get({ model: "discuss.channel", id: channel_id });

                if (thread) {
                    thread.update({ attention_state: attention_state, recently_terminated: recently_terminated });
                } else {
                    console.error("No thread found for channel id:", channel_id);
                }
            } else {
                notifications.forEach(notification => {
                    if (this.isDestroyed) return;
                    if (notification.type === "discuss.channel/new_message") {
                        
                        const { message } = notification.payload
                        
                        if (!message) return;

                        if (message.message_type === "whatsapp_message" && message.model === "discuss.channel" && message.res_id) {
                            const thread = this.store.Thread.get({ model: "discuss.channel", id: message.res_id });
                            if (thread) {
                                this.fetchLastMesage(thread);
                            }
                        }
                    }
                });

            }
        } catch (error) {
            if (this.isDestroyed) return;
            console.error("Failed to update attention state:", error);
        }
    },
    async fetchLastMesage(thread) {
        if (this.isDestroyed) return;
        try {
            const results = await this.sequential(() =>
                this.ormService.call("discuss.channel", "get_last_channel_message", [
                    thread.id
                ])
            );
            if (this.isDestroyed) return;
            if (!results) {
                return;
            }
            thread.update({ last_message_trucated: results });
        } catch (error) {
            if (this.isDestroyed) return;
            console.error("Failed to fetch last message:", error);
        }
    }
});