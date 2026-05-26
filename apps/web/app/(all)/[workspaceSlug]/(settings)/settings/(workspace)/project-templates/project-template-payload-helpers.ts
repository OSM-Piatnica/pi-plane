import type { TProjectTemplateCustomProperty, TProjectTemplatePayload } from "@plane/types";
import type { TCustomPropertyTemplateField, TProjectTemplateFormFields } from "./project-template-form.types";

const isHexColor = (value: string) => /^#[0-9A-Fa-f]{6}$/.test(value);

const mapCustomPropertyToPayload = (row: TCustomPropertyTemplateField): TProjectTemplateCustomProperty => {
  const base: TProjectTemplateCustomProperty = {
    title: row.title.trim(),
    description: row.description.trim() || undefined,
    is_mandatory: row.isMandatory,
    is_active: row.isActive,
    property_type: row.propertyType,
  };
  if (row.propertyType === "dropdown") {
    base.options = row.options.map((o) => o.trim()).filter(Boolean);
    base.select_mode = row.selectMode;
    if (row.selectMode === "single" && row.defaultOption && base.options?.includes(row.defaultOption)) {
      base.default_option = row.defaultOption;
    }
  }
  return base;
};

export const buildProjectTemplatePayloadFromFormValues = (
  values: TProjectTemplateFormFields
): TProjectTemplatePayload => {
  const payload: TProjectTemplatePayload = {};

  if (values.projectName.trim()) payload.name = values.projectName.trim();
  if (values.projectIdentifier.trim()) payload.identifier = values.projectIdentifier.trim().toUpperCase();
  if (values.projectDescription.trim()) payload.description = values.projectDescription.trim();
  if (values.projectLeadId) payload.project_lead = values.projectLeadId;
  if (values.defaultAssigneeId) payload.default_assignee = values.defaultAssigneeId;
  if (values.coverImageUrl.trim()) payload.cover_image_url = values.coverImageUrl.trim();
  if (values.startDate) payload.start_date = values.startDate;
  if (values.targetDate) payload.target_date = values.targetDate;
  payload.network = values.network;

  payload.cycle_view = values.features.cycle_view;
  payload.module_view = values.features.module_view;
  payload.issue_views_view = values.features.issue_views_view;
  payload.page_view = values.features.page_view;
  payload.intake_view = values.features.intake_view;
  payload.is_time_tracking_enabled = values.features.is_time_tracking_enabled;
  payload.is_issue_type_enabled = values.features.is_issue_type_enabled;

  if (values.features.is_issue_type_enabled) {
    payload.task_custom_properties = values.taskCustomProperties
      .filter((row) => row.title.trim())
      .map(mapCustomPropertyToPayload);
    payload.epic_enabled = values.epicEnabled;
    if (values.epicEnabled) {
      payload.epic_custom_properties = values.epicCustomProperties
        .filter((row) => row.title.trim())
        .map(mapCustomPropertyToPayload);
    }
    payload.additional_work_item_types = values.additionalWorkItemTypes
      .filter((row) => row.name.trim())
      .map((row) => ({
        name: row.name.trim(),
        description: row.description.trim() || undefined,
        custom_properties: row.customProperties.filter((p) => p.title.trim()).map(mapCustomPropertyToPayload),
      }));
  }

  payload.state_templates = values.stateTemplates
    .map((state) => ({
      name: state.name.trim(),
      group: state.group,
      color: isHexColor(state.color) ? state.color : undefined,
      default: state.default,
    }))
    .filter((state) => state.name.length > 0);

  payload.label_templates = values.labelTemplates
    .map((label) => ({
      name: label.name.trim(),
      color: isHexColor(label.color) ? label.color : undefined,
    }))
    .filter((label) => label.name.length > 0);

  return payload;
};
