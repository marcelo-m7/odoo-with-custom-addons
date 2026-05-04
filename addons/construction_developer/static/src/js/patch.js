import { patch } from "@web/core/utils/patch";
import { ORM } from "@web/core/orm_service";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { ListRenderer } from "@web/views/list/list_renderer";

// In the Remarks search/kanban views, displays only project-specific remark stages when grouping by stage_id
patch(RelationalModel.prototype, { async _postprocessReadGroup(config, { groups, length }) {
    let { groups: res_groups } = await super._postprocessReadGroup(config, { groups, length });
    // because multiple nested groupbys are possible, we need to check if stage_id is the current groupby
    if (config.resModel == "construction.remark" && groups.length > 0  && res_groups.length > 0 && (config.groupBy.includes("stage_id")) && groups[0].stage_id) {
        const stageIdsProjectsList = (await this.env.services.orm.searchRead("construction.remark.stage", [], ['id', 'project_ids', 'sequence']));
        res_groups = res_groups.filter((group) => stageIdsProjectsList.some((stage) => stage.id === group.rawValue[0] && stage.project_ids.includes(config.context.default_project_id)))
                               .map((group) => { group.sequence = stageIdsProjectsList.find((stage) => stage.id === group.rawValue[0]).sequence; return group; }).sort((group_a, group_b) => group_a.sequence - group_b.sequence);}
    return { groups: res_groups, length: res_groups.length };}});

// In the Remarks kanban view, allow the user to drag and drop remark stages to reorder them like project stages, and save the new order in the sequence field
patch(ORM.prototype, { webResequence(model, ids, kwargs = {}) { return super.webResequence(model, ids, model === "construction.remark.stage" ? { ...kwargs, 'specification': {'sequence': {}}, 'field_name': "sequence" } : kwargs); }});

// In the Cost Nature Analysis list view, 
// Computes the margin % from the summed costs & prices instead of summing margin percentages
patch(ListRenderer.prototype, { formatGroupAggregate(group, column) {
    // Writes the correct margin % in the grouped list items 
        if (group.model.config.resModel == "construction.cost.nature.analysis.report" && ["quantity", "margin_percent"].includes(column.name)) {
            return { value: (column.name == "margin_percent" && group.aggregates["total_price"]) ? Math.round(100 * (group.aggregates["margin"]) / group.aggregates["total_price"]).toString() + " %" : "" };}
        return super.formatGroupAggregate(group, column);},
    // Writes the correct margin % in the aggregate line below the list
    computeAggregates() { const aggregates = super.computeAggregates();
        if (aggregates && aggregates["margin_percent"] && aggregates["total_price"] && aggregates["margin"]) {
            aggregates["margin_percent"].rawValue = aggregates["total_price"].rawValue ? 100 * (aggregates["margin"].rawValue) / aggregates["total_price"].rawValue : 0;
            aggregates["margin_percent"].value = Math.round(aggregates["margin_percent"].rawValue).toString() + " %";}
        return aggregates;}})
