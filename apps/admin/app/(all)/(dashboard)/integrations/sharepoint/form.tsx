/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Controller, useForm } from "react-hook-form";
// plane internal packages
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { setToast } from "@plane/blocks/toast";
import type { IFormattedInstanceConfiguration, TInstanceSharePointConfigurationKeys } from "@plane/types";
import {
  SHAREPOINT_DEFAULT_MAX_FILE_SIZE,
  SHAREPOINT_MAX_MAX_FILE_SIZE,
  SHAREPOINT_MIN_MAX_FILE_SIZE,
  bytesToMegabytesText,
  getSharePointMaxFileSize,
  sharePointMaxFileSizeToSave,
} from "@plane/utils";
// components
import { CodeBlock } from "@/components/common/code-block";
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
// hooks
import { useInstance } from "@/hooks/store";
// local
import { SharePointConnectionTest } from "./test-connection";

type Props = {
  config: IFormattedInstanceConfiguration;
};

/** The switch is saved from the header of the page; the size is edited in megabytes and saved in bytes. */
type SharePointFormValues = Record<Exclude<TInstanceSharePointConfigurationKeys, "IS_SHAREPOINT_ENABLED">, string>;

type TApiError = { error?: string };

const ENTRA_APP_REGISTRATIONS_URL =
  "https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade";
const MAX_FILE_SIZE_DESCRIPTION_ID = "SHAREPOINT_MAX_FILE_SIZE-description";
const DEFAULT_MAX_FILE_SIZE_MB = bytesToMegabytesText(SHAREPOINT_DEFAULT_MAX_FILE_SIZE);
const MIN_MAX_FILE_SIZE_MB = bytesToMegabytesText(SHAREPOINT_MIN_MAX_FILE_SIZE);
const MAX_MAX_FILE_SIZE_MB = bytesToMegabytesText(SHAREPOINT_MAX_MAX_FILE_SIZE);
const FORM_KEYS = [
  "SHAREPOINT_TENANT_ID",
  "SHAREPOINT_CLIENT_ID",
  "SHAREPOINT_CLIENT_SECRET",
  "SHAREPOINT_MAX_FILE_SIZE",
] as const satisfies readonly (keyof SharePointFormValues)[];

const formValues = (config: IFormattedInstanceConfiguration): SharePointFormValues => {
  const size = getSharePointMaxFileSize(config.SHAREPOINT_MAX_FILE_SIZE);
  return {
    SHAREPOINT_TENANT_ID: config.SHAREPOINT_TENANT_ID ?? "",
    SHAREPOINT_CLIENT_ID: config.SHAREPOINT_CLIENT_ID ?? "",
    SHAREPOINT_CLIENT_SECRET: config.SHAREPOINT_CLIENT_SECRET ?? "",
    // Shown exactly as saved (in megabytes, not rounded); empty while the default applies
    SHAREPOINT_MAX_FILE_SIZE: size.isDefault ? "" : bytesToMegabytesText(size.applied),
  };
};

export function InstanceSharePointConfigForm(props: Props) {
  const { config } = props;
  // store
  const { updateInstanceConfigurations } = useInstance();
  // form data
  const {
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty, dirtyFields, isSubmitting },
  } = useForm<SharePointFormValues>({ defaultValues: formValues(config) });
  // What the server applies now, from what is saved (not from what is being typed)
  const savedSize = getSharePointMaxFileSize(config.SHAREPOINT_MAX_FILE_SIZE);

  const hasSavedCredentials =
    Boolean(config.SHAREPOINT_TENANT_ID) &&
    Boolean(config.SHAREPOINT_CLIENT_ID) &&
    Boolean(config.SHAREPOINT_CLIENT_SECRET);

  const credentialFields: TControllerInputFormField<SharePointFormValues>[] = [
    {
      key: "SHAREPOINT_TENANT_ID",
      type: "text",
      label: "Directory (tenant) ID",
      description: (
        <>
          Shown on the Overview page of the{" "}
          <a
            href={ENTRA_APP_REGISTRATIONS_URL}
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
          >
            app registration in Microsoft Entra
          </a>
          .
        </>
      ),
      placeholder: "72f988bf-86f1-41af-91ab-2d7cd011db47",
      error: Boolean(errors.SHAREPOINT_TENANT_ID),
      required: true,
    },
    {
      key: "SHAREPOINT_CLIENT_ID",
      type: "text",
      label: "Application (client) ID",
      description: (
        <>
          Of the app registration that holds the <CodeBlock darkerShade>Sites.Selected</CodeBlock> application
          permission for Microsoft Graph.
        </>
      ),
      placeholder: "6731de76-14a6-49ae-97bc-6eba6914391e",
      error: Boolean(errors.SHAREPOINT_CLIENT_ID),
      required: true,
    },
    {
      key: "SHAREPOINT_CLIENT_SECRET",
      type: "password",
      label: "Client secret",
      description: (
        <>
          The value of a secret from <CodeBlock darkerShade>Certificates &amp; secrets</CodeBlock>, not its ID. It is
          stored encrypted.
        </>
      ),
      placeholder: "Client secret value",
      error: Boolean(errors.SHAREPOINT_CLIENT_SECRET),
      required: true,
    },
  ];

  const onSubmit = async (formData: SharePointFormValues) => {
    const values: SharePointFormValues = {
      SHAREPOINT_TENANT_ID: formData.SHAREPOINT_TENANT_ID.trim(),
      SHAREPOINT_CLIENT_ID: formData.SHAREPOINT_CLIENT_ID.trim(),
      SHAREPOINT_CLIENT_SECRET: formData.SHAREPOINT_CLIENT_SECRET.trim(),
      SHAREPOINT_MAX_FILE_SIZE: formData.SHAREPOINT_MAX_FILE_SIZE.trim(),
    };
    // Only what the administrator changed is sent: a value saved elsewhere (the environment, the API) stays as it is
    const payload: Partial<SharePointFormValues> = {};
    for (const key of FORM_KEYS) {
      if (!dirtyFields[key]) continue;
      payload[key] =
        key === "SHAREPOINT_MAX_FILE_SIZE" ? (sharePointMaxFileSizeToSave(values[key]) ?? values[key]) : values[key];
    }
    try {
      await updateInstanceConfigurations(payload);
      // What was saved is the new starting point: the form is clean and the connection can be tested
      reset(values);
      setToast({ type: "success", title: "Success", message: "SharePoint settings saved" });
    } catch (error) {
      setToast({
        type: "error",
        title: "Error",
        message: (error as TApiError)?.error ?? "The SharePoint settings could not be saved",
      });
    }
  };

  const blockedReason = isDirty
    ? "Save your changes first: the test uses the saved settings."
    : hasSavedCredentials
      ? undefined
      : "Save the tenant ID, the client ID and the client secret first.";

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div>
          <div className="pb-1 text-18 font-medium text-primary">App registration</div>
          <div className="text-13 font-regular text-tertiary">
            Pi-Plane signs in to Microsoft Graph as the application itself and reaches only the sites a SharePoint
            administrator granted to it.
          </div>
        </div>
        <div className="grid w-full grid-cols-1 items-start gap-x-12 gap-y-8 lg:grid-cols-2">
          {credentialFields.map((field) => (
            <ControllerInput
              key={field.key}
              control={control}
              type={field.type}
              name={field.key}
              label={field.label}
              description={field.description}
              placeholder={field.placeholder}
              error={field.error}
              required={field.required}
            />
          ))}
          <div className="flex flex-col gap-1">
            <label htmlFor="SHAREPOINT_MAX_FILE_SIZE" className="text-13 text-tertiary">
              Largest file (MB)
            </label>
            <InputGroup size="lg">
              <Controller
                control={control}
                name="SHAREPOINT_MAX_FILE_SIZE"
                rules={{
                  validate: (value) =>
                    sharePointMaxFileSizeToSave(value) !== undefined ||
                    `Enter a size from ${MIN_MAX_FILE_SIZE_MB} to ${Number(MAX_MAX_FILE_SIZE_MB).toLocaleString()} MB.`,
                }}
                render={({ field: { value, onChange, ref } }) => (
                  <Input
                    size="lg"
                    id="SHAREPOINT_MAX_FILE_SIZE"
                    name="SHAREPOINT_MAX_FILE_SIZE"
                    type="number"
                    min={MIN_MAX_FILE_SIZE_MB}
                    max={MAX_MAX_FILE_SIZE_MB}
                    step="any"
                    value={value}
                    onChange={onChange}
                    ref={ref}
                    aria-invalid={Boolean(errors.SHAREPOINT_MAX_FILE_SIZE)}
                    aria-describedby={MAX_FILE_SIZE_DESCRIPTION_ID}
                    placeholder={DEFAULT_MAX_FILE_SIZE_MB}
                  />
                )}
              />
            </InputGroup>
            <p id={MAX_FILE_SIZE_DESCRIPTION_ID} className="pt-0.5 text-11 text-tertiary">
              The largest file a person can put in SharePoint through Pi-Plane. Leave empty for the default of{" "}
              {DEFAULT_MAX_FILE_SIZE_MB} MB. It is apart from the upload limit on the General page. In force now:{" "}
              {bytesToMegabytesText(savedSize.applied)} MB{savedSize.isDefault ? " (the default)" : ""}.
            </p>
            {savedSize.ignoredValue !== undefined && (
              <p className="text-11 text-danger-primary">
                The saved value “{savedSize.ignoredValue}” is not a size from {MIN_MAX_FILE_SIZE_MB} to{" "}
                {Number(MAX_MAX_FILE_SIZE_MB).toLocaleString()} MB in bytes, so the default of{" "}
                {DEFAULT_MAX_FILE_SIZE_MB} MB applies. Enter a size and save to replace it.
              </p>
            )}
            {errors.SHAREPOINT_MAX_FILE_SIZE?.message && (
              <p className="text-11 text-danger-primary">{errors.SHAREPOINT_MAX_FILE_SIZE.message}</p>
            )}
          </div>
        </div>
        <div>
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            onClick={handleSubmit(onSubmit)}
            loading={isSubmitting}
            disabled={!isDirty || isSubmitting}
            label={isSubmitting ? "Saving" : "Save changes"}
          />
        </div>
      </div>

      <SharePointConnectionTest blockedReason={blockedReason} />
    </div>
  );
}
