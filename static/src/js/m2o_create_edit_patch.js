/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

patch(Many2XAutocomplete.prototype, {
    addCreateEditSuggestion() {
        return this.activeActions.createEdit ?? this.activeActions.create;
    },

    addStartTypingSuggestion() {
        return false;
    },
});