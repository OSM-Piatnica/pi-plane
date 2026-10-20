/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Switch } from "@makeplane/propel/components/switch";
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import { Select } from "@plane/blocks/select";
import type { TCustomPropertyTemplateField, TCustomPropertyType } from "./project-template-form.types";
import { CUSTOM_PROPERTY_TYPES, DEFAULT_CUSTOM_PROPERTY } from "./project-template-form.types";

type TTemplateSelectOption = { value: string; label: string };

type TTemplateSelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: TTemplateSelectOption[];
  id?: string;
};

function TemplateSelect({ value, onChange, options, id }: TTemplateSelectProps) {
  const selected = options.find((option) => option.value === value) ?? null;
  return (
    <Select<TTemplateSelectOption>
      getValues={() => options}
      value={selected}
      onChange={onChange}
      getOptionValue={(option) => option.value}
      getOptionLabel={(option) => option.label}
      showSearch={false}
      pinSelected={false}
    >
      <Select.Trigger id={id} variant="select-lg" className="w-full">
        <Select.Value />
      </Select.Trigger>
    </Select>
  );
}

type TProps = {
  properties: TCustomPropertyTemplateField[];
  onChange: (next: TCustomPropertyTemplateField[]) => void;
  emptyHint: string;
};

export const CustomPropertiesTemplateEditor = ({ properties, onChange, emptyHint }: TProps) => {
  const { t } = useTranslation();
  const idPrefix = useId();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<TCustomPropertyTemplateField | null>(null);
  const [optionDraft, setOptionDraft] = useState("");

  const propertyTypeLabel = (type: TCustomPropertyType) =>
    t(`workspace_settings.settings.project_templates.form.custom_property.types.${type}`);

  const resetDraft = () => {
    setDraft(null);
    setEditingId(null);
    setOptionDraft("");
  };

  const startAdd = () => {
    const next = DEFAULT_CUSTOM_PROPERTY();
    setDraft(next);
    setEditingId(next.id);
  };

  const startEdit = (row: TCustomPropertyTemplateField) => {
    setDraft({ ...row, options: [...row.options] });
    setEditingId(row.id);
    setOptionDraft("");
  };

  const saveDraft = () => {
    if (!draft || !draft.title.trim()) return;
    const normalized: TCustomPropertyTemplateField = {
      ...draft,
      title: draft.title.trim(),
      description: draft.description.trim(),
      options: draft.propertyType === "dropdown" ? draft.options.filter((o) => o.trim()) : [],
      defaultOption:
        draft.propertyType === "dropdown" && draft.defaultOption && draft.options.includes(draft.defaultOption)
          ? draft.defaultOption
          : null,
    };
    const exists = properties.some((p) => p.id === normalized.id);
    onChange(exists ? properties.map((p) => (p.id === normalized.id ? normalized : p)) : [...properties, normalized]);
    resetDraft();
  };

  const removeProperty = (id: string) => {
    onChange(properties.filter((p) => p.id !== id));
    if (editingId === id) resetDraft();
  };

  const patchDraft = (patch: Partial<TCustomPropertyTemplateField>) => {
    if (!draft) return;
    const next = { ...draft, ...patch };
    if (patch.propertyType && patch.propertyType !== "dropdown") {
      next.options = [];
      next.defaultOption = null;
    }
    setDraft(next);
  };

  const addOption = () => {
    if (!draft || !optionDraft.trim()) return;
    const label = optionDraft.trim();
    if (draft.options.includes(label)) {
      setOptionDraft("");
      return;
    }
    patchDraft({ options: [...draft.options, label] });
    setOptionDraft("");
  };

  const removeOption = (option: string) => {
    if (!draft) return;
    const options = draft.options.filter((o) => o !== option);
    patchDraft({
      options,
      defaultOption: draft.defaultOption === option ? null : draft.defaultOption,
    });
  };

  return (
    <div className="space-y-2">
      {properties.length === 0 && !draft ? <p className="text-12 text-tertiary">{emptyHint}</p> : null}
      {properties
        .filter((p) => p.id !== editingId)
        .map((property) => (
          <div
            key={property.id}
            className="flex items-start justify-between gap-2 rounded-md border border-subtle bg-surface-2 px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <p className="text-13 font-medium text-primary">{property.title}</p>
              <p className="text-11 text-tertiary">
                {propertyTypeLabel(property.propertyType)}
                {property.isMandatory
                  ? ` · ${t("workspace_settings.settings.project_templates.form.custom_property.mandatory")}`
                  : ""}
                {!property.isActive
                  ? ` · ${t("workspace_settings.settings.project_templates.form.custom_property.inactive")}`
                  : ""}
              </p>
            </div>
            <div className="flex shrink-0 gap-1">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                stretch="auto"
                onClick={() => startEdit(property)}
                label={t("edit")}
              />
              <button
                type="button"
                className="rounded-md p-1.5 text-tertiary hover:bg-surface-1 hover:text-danger-primary"
                onClick={() => removeProperty(property.id)}
                aria-label={t("remove")}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}

      {draft ? (
        <div className="space-y-3 rounded-md border border-subtle bg-surface-2 p-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label htmlFor={`${idPrefix}-title`} className="text-12 text-tertiary">
                {t("workspace_settings.settings.project_templates.form.custom_property.title_label")}
              </label>
              <div className="mt-1">
                <InputGroup size="lg">
                  <Input
                    id={`${idPrefix}-title`}
                    size="lg"
                    value={draft.title}
                    onChange={(e) => patchDraft({ title: e.target.value })}
                    placeholder={t(
                      "workspace_settings.settings.project_templates.form.custom_property.title_placeholder"
                    )}
                  />
                </InputGroup>
              </div>
            </div>
            <div>
              <label htmlFor={`${idPrefix}-type`} className="text-12 text-tertiary">
                {t("workspace_settings.settings.project_templates.form.custom_property.type_label")}
              </label>
              <div className="mt-1">
                <TemplateSelect
                  id={`${idPrefix}-type`}
                  value={draft.propertyType}
                  onChange={(value) => patchDraft({ propertyType: value as TCustomPropertyType })}
                  options={CUSTOM_PROPERTY_TYPES.map((type) => ({ value: type, label: propertyTypeLabel(type) }))}
                />
              </div>
            </div>
          </div>
          <div>
            <label htmlFor={`${idPrefix}-description`} className="text-12 text-tertiary">
              {t("workspace_settings.settings.project_templates.form.custom_property.description_label")}
            </label>
            <div className="mt-1">
              <TextAreaGroup resize="vertical">
                <TextArea
                  id={`${idPrefix}-description`}
                  size="md"
                  surface="field"
                  rows={2}
                  value={draft.description}
                  onChange={(e) => patchDraft({ description: e.target.value })}
                  placeholder={t(
                    "workspace_settings.settings.project_templates.form.custom_property.description_placeholder"
                  )}
                />
              </TextAreaGroup>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-6">
            <label className="flex items-center gap-2 text-13 text-secondary">
              <input
                type="checkbox"
                checked={draft.isMandatory}
                onChange={(e) => patchDraft({ isMandatory: e.target.checked })}
              />
              {t("workspace_settings.settings.project_templates.form.custom_property.mandatory_checkbox")}
            </label>
            <label className="flex items-center gap-2 text-13 text-secondary">
              <Switch checked={draft.isActive} onCheckedChange={(v) => patchDraft({ isActive: v })} size="sm" />
              {t("workspace_settings.settings.project_templates.form.custom_property.active_checkbox")}
            </label>
          </div>
          {draft.propertyType === "dropdown" ? (
            <div className="space-y-2 rounded-md border border-subtle bg-surface-1 p-3">
              <p className="text-12 font-medium text-primary">
                {t("workspace_settings.settings.project_templates.form.custom_property.dropdown_options_heading")}
              </p>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label htmlFor={`${idPrefix}-select-mode`} className="text-12 text-tertiary">
                    {t("workspace_settings.settings.project_templates.form.custom_property.select_mode_label")}
                  </label>
                  <div className="mt-1">
                    <TemplateSelect
                      id={`${idPrefix}-select-mode`}
                      value={draft.selectMode}
                      onChange={(value) =>
                        patchDraft({
                          selectMode: value as TCustomPropertyTemplateField["selectMode"],
                          defaultOption: null,
                        })
                      }
                      options={[
                        {
                          value: "single",
                          label: t("workspace_settings.settings.project_templates.form.custom_property.select_single"),
                        },
                        {
                          value: "multi",
                          label: t("workspace_settings.settings.project_templates.form.custom_property.select_multi"),
                        },
                      ]}
                    />
                  </div>
                </div>
                {draft.selectMode === "single" && draft.options.length > 0 ? (
                  <div>
                    <label htmlFor={`${idPrefix}-default-option`} className="text-12 text-tertiary">
                      {t("workspace_settings.settings.project_templates.form.custom_property.default_option_label")}
                    </label>
                    <div className="mt-1">
                      <TemplateSelect
                        id={`${idPrefix}-default-option`}
                        value={draft.defaultOption ?? ""}
                        onChange={(value) => patchDraft({ defaultOption: value || null })}
                        options={[
                          {
                            value: "",
                            label: t("workspace_settings.settings.project_templates.form.custom_property.no_default"),
                          },
                          ...draft.options.map((opt) => ({ value: opt, label: opt })),
                        ]}
                      />
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="space-y-1.5">
                {draft.options.map((opt) => (
                  <div key={opt} className="flex items-center justify-between rounded border border-subtle px-2 py-1">
                    <span className="text-13 text-primary">{opt}</span>
                    <button
                      type="button"
                      className="text-tertiary hover:text-danger-primary"
                      aria-label={t("common.remove")}
                      onClick={() => removeOption(opt)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <div className="min-w-0 flex-1">
                  <InputGroup size="lg">
                    <Input
                      size="lg"
                      value={optionDraft}
                      onChange={(e) => setOptionDraft(e.target.value)}
                      placeholder={t(
                        "workspace_settings.settings.project_templates.form.custom_property.option_placeholder"
                      )}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addOption();
                        }
                      }}
                    />
                  </InputGroup>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  stretch="auto"
                  onClick={addOption}
                  disabled={!optionDraft.trim()}
                  label={t("add")}
                />
              </div>
            </div>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              stretch="auto"
              onClick={resetDraft}
              label={t("cancel")}
            />
            <Button
              type="button"
              variant="primary"
              size="sm"
              stretch="auto"
              onClick={saveDraft}
              disabled={!draft.title.trim()}
              label={editingId && properties.some((p) => p.id === editingId) ? t("update") : t("add")}
            />
          </div>
        </div>
      ) : null}

      {!draft ? (
        <button
          type="button"
          className="flex items-center gap-1 text-12 font-medium text-secondary hover:text-primary"
          onClick={startAdd}
        >
          <Plus className="h-3.5 w-3.5" />
          {t("workspace_settings.settings.project_templates.form.custom_property.add_property")}
        </button>
      ) : null}
    </div>
  );
};
