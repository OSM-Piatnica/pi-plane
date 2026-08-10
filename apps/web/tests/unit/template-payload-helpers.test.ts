import { describe, expect, it } from "vitest";
import type { TProjectTemplate, TWorkItemTemplate } from "@plane/types";
import {
  buildWorkItemTemplatePayloadFromFormValues,
  descriptionHtmlToPlain,
  mapWorkItemTemplateToFormValues,
  plainTextToDescriptionHtml,
} from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/work-item-templates/work-item-template-payload-helpers";
import {
  buildProjectTemplatePayloadFromFormValues,
  mapProjectTemplateToFormValues,
} from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/project-templates/project-template-payload-helpers";
import { DEFAULT_FEATURE_TOGGLES } from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/project-templates/project-template-form.types";

describe("work item template payload helpers", () => {
  it("round-trips plain description through html", () => {
    const plain = "Line one\nLine two";
    expect(descriptionHtmlToPlain(plainTextToDescriptionHtml(plain))).toBe(plain);
  });

  it("maps API template to form values and back", () => {
    const template: TWorkItemTemplate = {
      id: "tpl-1",
      name: "Bug",
      description: "Note",
      project_id: "proj-1",
      sort_order: 1,
      created_at: "",
      updated_at: "",
      payload: {
        name: "Bug title",
        description_html: "<p>Details</p>",
        priority: "high",
        state_id: "state-1",
        label_ids: ["label-1"],
      },
    };

    const formValues = mapWorkItemTemplateToFormValues(template);
    expect(formValues.templateName).toBe("Bug");
    expect(formValues.workItemName).toBe("Bug title");
    expect(formValues.workItemDescriptionPlain).toBe("Details");
    expect(formValues.priority).toBe("high");

    const payload = buildWorkItemTemplatePayloadFromFormValues(formValues);
    expect(payload.name).toBe("Bug title");
    expect(payload.priority).toBe("high");
    expect(payload.state_id).toBe("state-1");
    expect(payload.label_ids).toEqual(["label-1"]);
  });
});

describe("project template payload helpers", () => {
  it("maps API template to form values and back", () => {
    const template: TProjectTemplate = {
      id: "pt-1",
      name: "Delivery",
      description: "Note",
      sort_order: 1,
      created_at: "",
      updated_at: "",
      payload: {
        name: "Product",
        identifier: "PROD",
        description: "Project desc",
        cycle_view: true,
        module_view: false,
        is_issue_type_enabled: true,
        epic_enabled: true,
        state_templates: [{ name: "Todo", group: "unstarted", color: "#3F76FF", default: true }],
        label_templates: [{ name: "Bug", color: "#FF6B6B" }],
        task_custom_properties: [
          {
            title: "Severity",
            is_mandatory: true,
            is_active: true,
            property_type: "dropdown",
            options: ["Low", "High"],
            select_mode: "single",
            default_option: "Low",
          },
        ],
      },
    };

    const formValues = mapProjectTemplateToFormValues(template);
    expect(formValues.templateName).toBe("Delivery");
    expect(formValues.projectName).toBe("Product");
    expect(formValues.projectIdentifier).toBe("PROD");
    expect(formValues.features.cycle_view).toBe(true);
    expect(formValues.features.module_view).toBe(false);
    expect(formValues.epicEnabled).toBe(true);
    expect(formValues.stateTemplates).toHaveLength(1);
    expect(formValues.labelTemplates).toHaveLength(1);
    expect(formValues.taskCustomProperties[0]?.title).toBe("Severity");

    const payload = buildProjectTemplatePayloadFromFormValues({
      ...formValues,
      features: { ...DEFAULT_FEATURE_TOGGLES, is_issue_type_enabled: true },
    });
    expect(payload.name).toBe("Product");
    expect(payload.identifier).toBe("PROD");
    expect(payload.state_templates?.[0]?.name).toBe("Todo");
    expect(payload.label_templates?.[0]?.name).toBe("Bug");
    expect(payload.task_custom_properties?.[0]?.title).toBe("Severity");
  });
});
