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
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import { Switch } from "@makeplane/propel/components/switch";
import type { TIssueTypePropertyType } from "@plane/types";
import {
  CUSTOM_PROPERTY_TYPES,
  DEFAULT_WORK_ITEM_TYPE_PROPERTY,
  type TWorkItemTypeFormProperty,
} from "./work-item-type-form.types";
import { ProjectTemplateSelectField } from "../project-templates/project-template-select-field";

type TProps = {
  properties: TWorkItemTypeFormProperty[];
  onChange: (next: TWorkItemTypeFormProperty[]) => void;
};

export const WorkItemTypePropertyEditor = ({ properties, onChange }: TProps) => {
  const { t } = useTranslation();
  const idPrefix = useId();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<TWorkItemTypeFormProperty | null>(null);
  const [optionDraft, setOptionDraft] = useState("");

  const propertyTypeLabel = (type: TIssueTypePropertyType) =>
    t(`workspace_settings.settings.work_item_types.form.property.types.${type}`);

  const resetDraft = () => {
    setDraft(null);
    setEditingId(null);
    setOptionDraft("");
  };

  const startAdd = () => {
    const next = DEFAULT_WORK_ITEM_TYPE_PROPERTY();
    setDraft(next);
    setEditingId(next.id);
  };

  const startEdit = (row: TWorkItemTypeFormProperty) => {
    setDraft({ ...row, options: [...row.options] });
    setEditingId(row.id);
    setOptionDraft("");
  };

  const saveDraft = () => {
    if (!draft || !draft.title.trim()) return;
    const normalized: TWorkItemTypeFormProperty = {
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

  const patchDraft = (patch: Partial<TWorkItemTypeFormProperty>) => {
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
    patchDraft({
      options: draft.options.filter((o) => o !== option),
      defaultOption: draft.defaultOption === option ? null : draft.defaultOption,
    });
  };

  return (
    <div className="space-y-2">
      {properties.length === 0 && !draft ? (
        <p className="text-12 text-tertiary">{t("workspace_settings.settings.work_item_types.form.property.empty")}</p>
      ) : null}
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
                  ? ` · ${t("workspace_settings.settings.work_item_types.form.property.mandatory")}`
                  : ""}
                {!property.isActive
                  ? ` · ${t("workspace_settings.settings.work_item_types.form.property.inactive")}`
                  : ""}
              </p>
            </div>
            <div className="flex shrink-0 gap-1">
              <Button
                stretch="auto"
                type="button"
                variant="secondary"
                size="sm"
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
                {t("workspace_settings.settings.work_item_types.form.property.title_label")}
              </label>
              <div className="mt-1">
                <InputGroup size="md">
                  <Input
                    id={`${idPrefix}-title`}
                    value={draft.title}
                    onChange={(e) => patchDraft({ title: e.target.value })}
                    size="md"
                  />
                </InputGroup>
              </div>
            </div>
            <div>
              <span id={`${idPrefix}-type-label`} className="text-12 text-tertiary">
                {t("workspace_settings.settings.work_item_types.form.property.type_label")}
              </span>
              <div className="mt-1" role="group" aria-labelledby={`${idPrefix}-type-label`}>
                <ProjectTemplateSelectField<TIssueTypePropertyType>
                  value={draft.propertyType}
                  onChange={(value) => patchDraft({ propertyType: value })}
                  options={CUSTOM_PROPERTY_TYPES.map((type) => ({ value: type, label: propertyTypeLabel(type) }))}
                />
              </div>
            </div>
          </div>
          <div>
            <label htmlFor={`${idPrefix}-description`} className="text-12 text-tertiary">
              {t("workspace_settings.settings.work_item_types.form.property.description_label")}
            </label>
            <div className="mt-1">
              <TextAreaGroup>
                <TextArea
                  id={`${idPrefix}-description`}
                  size="md"
                  surface="field"
                  rows={2}
                  value={draft.description}
                  onChange={(e) => patchDraft({ description: e.target.value })}
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
              {t("workspace_settings.settings.work_item_types.form.property.mandatory_checkbox")}
            </label>
            <label className="flex items-center gap-2 text-13 text-secondary">
              <Switch checked={draft.isActive} onCheckedChange={(v) => patchDraft({ isActive: v })} size="sm" />
              {t("workspace_settings.settings.work_item_types.form.property.active_checkbox")}
            </label>
          </div>
          {draft.propertyType === "dropdown" ? (
            <div className="space-y-2 rounded-md border border-subtle bg-surface-1 p-3">
              <div className="flex items-center gap-2">
                <div className="flex-1">
                  <InputGroup size="md">
                    <Input
                      size="md"
                      value={optionDraft}
                      onChange={(e) => setOptionDraft(e.target.value)}
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
                  stretch="auto"
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={addOption}
                  disabled={!optionDraft.trim()}
                  label={t("add")}
                />
              </div>
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
          ) : null}
          <div className="flex justify-end gap-2">
            <Button
              stretch="auto"
              type="button"
              variant="secondary"
              size="sm"
              onClick={resetDraft}
              label={t("cancel")}
            />
            <Button
              stretch="auto"
              type="button"
              variant="primary"
              size="sm"
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
          {t("workspace_settings.settings.work_item_types.form.property.add")}
        </button>
      ) : null}
    </div>
  );
};
