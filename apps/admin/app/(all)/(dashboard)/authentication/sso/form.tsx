/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { isEmpty } from "lodash-es";
import Link from "next/link";
import { Controller, useForm } from "react-hook-form";
// plane internal packages
import { API_BASE_URL } from "@plane/constants";
import type { TOidcProviderDefinition } from "@plane/constants";
import { Button } from "@makeplane/propel/components/button";
import { Switch } from "@makeplane/propel/components/switch";
import { setToast } from "@plane/blocks/toast";
import type { IFormattedInstanceConfiguration } from "@plane/types";
// components
import { CodeBlock } from "@/components/common/code-block";
import { ConfirmDiscardModal } from "@/components/common/confirm-discard-modal";
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
import type { TControllerSwitchFormField } from "@/components/common/controller-switch";
import { ControllerSwitch } from "@/components/common/controller-switch";
import type { TCopyField } from "@/components/common/copy-field";
import { CopyField } from "@/components/common/copy-field";
// hooks
import { useInstance } from "@/hooks/store";

type Props = {
  provider: TOidcProviderDefinition;
  config: IFormattedInstanceConfiguration;
};

// Keyed by the full name of the instance setting, e.g. ENTRA_TENANT_ID
type OidcConfigFormValues = Record<string, string>;

const isOn = (value: string | undefined) => {
  const parsed = Number.parseInt(value ?? "0", 10);
  return !Number.isNaN(parsed) && parsed !== 0;
};

export function InstanceOidcConfigForm(props: Props) {
  const { provider, config } = props;
  const { prefix } = provider;
  const read = (name: string): string => (config as Record<string, string | undefined>)[name] ?? "";
  // states
  const [isDiscardChangesModalOpen, setIsDiscardChangesModalOpen] = useState(false);
  // store hooks
  const { updateInstanceConfigurations } = useInstance();
  // form data
  const names = [
    `${prefix}_CLIENT_ID`,
    `${prefix}_CLIENT_SECRET`,
    ...provider.fields.map((field) => `${prefix}_${field.name}`),
    `${prefix}_ALLOWED_EMAIL_DOMAINS`,
    `${prefix}_ENABLE_SIGNUP`,
    `ENABLE_${prefix}_SYNC`,
  ];
  const toFormValues = (source: (name: string) => string | undefined): OidcConfigFormValues =>
    Object.fromEntries(
      names.map((name) => {
        const fallback = name === `${prefix}_ENABLE_SIGNUP` ? "1" : name === `ENABLE_${prefix}_SYNC` ? "0" : "";
        return [name, source(name) || fallback];
      })
    );
  const {
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<OidcConfigFormValues>({ defaultValues: toFormValues(read) });

  const originURL = !isEmpty(API_BASE_URL) ? API_BASE_URL : typeof window !== "undefined" ? window.location.origin : "";

  const consoleLink = provider.consoleUrl ? (
    <a href={provider.consoleUrl} target="_blank" className="text-accent-primary hover:underline" rel="noreferrer">
      {provider.consoleName}.
    </a>
  ) : (
    <>{provider.consoleName}.</>
  );

  const FORM_FIELDS: TControllerInputFormField<OidcConfigFormValues>[] = [
    {
      key: `${prefix}_CLIENT_ID`,
      type: "text",
      label: "Client ID",
      description: <>You will get this from {consoleLink}</>,
      placeholder: "00000000-0000-0000-0000-000000000000",
      error: Boolean(errors[`${prefix}_CLIENT_ID`]),
      required: true,
    },
    {
      key: `${prefix}_CLIENT_SECRET`,
      type: "password",
      label: "Client secret",
      description: <>The client secret is created next to the client ID in {consoleLink}</>,
      placeholder: "client secret value",
      error: Boolean(errors[`${prefix}_CLIENT_SECRET`]),
      required: true,
    },
    ...provider.fields.map((field) => ({
      key: `${prefix}_${field.name}`,
      type: field.type,
      label: field.label,
      description: <>{field.description}</>,
      placeholder: field.placeholder ?? "",
      error: Boolean(errors[`${prefix}_${field.name}`]),
      required: field.required ?? false,
    })),
    {
      key: `${prefix}_ALLOWED_EMAIL_DOMAINS`,
      type: "text",
      label: "Allowed email domains",
      description: <>Optional. Comma-separated; only addresses of these domains can sign in.</>,
      placeholder: "example.com, example.org",
      error: Boolean(errors[`${prefix}_ALLOWED_EMAIL_DOMAINS`]),
      required: false,
    },
  ];

  const SYNC_SWITCH_FIELD: TControllerSwitchFormField<OidcConfigFormValues> = {
    name: `ENABLE_${prefix}_SYNC`,
    label: provider.name,
  };

  const SERVICE_FIELD: TCopyField[] = [
    {
      key: "Redirect_URI",
      label: "Redirect URI",
      url: `${originURL}/auth/oidc/${provider.key}/callback/`,
      description: (
        <>
          We will auto-generate this. Paste this into the <CodeBlock darkerShade>Redirect URI</CodeBlock> field of{" "}
          {provider.consoleName === "your identity provider" ? "your identity provider." : consoleLink}
        </>
      ),
    },
  ];

  const onSubmit = async (formData: OidcConfigFormValues) => {
    try {
      const response = await updateInstanceConfigurations({ ...formData });
      setToast({
        type: "success",
        title: "Done!",
        message: `Your ${provider.name} authentication is configured. You should test it now.`,
      });
      reset(toFormValues((name) => response.find((item) => item.key === name)?.value));
    } catch (err) {
      console.error(err);
    }
  };

  const handleGoBack = (e: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => {
    if (isDirty) {
      e.preventDefault();
      setIsDiscardChangesModalOpen(true);
    }
  };

  return (
    <>
      <ConfirmDiscardModal
        isOpen={isDiscardChangesModalOpen}
        onDiscardHref="/authentication"
        handleClose={() => setIsDiscardChangesModalOpen(false)}
      />
      <div className="flex flex-col gap-8">
        <div className="grid w-full grid-cols-2 gap-x-12 gap-y-8">
          <div className="col-span-2 flex flex-col gap-y-4 pt-1 md:col-span-1">
            <div className="pt-2.5 text-18 font-medium">{provider.name}-provided details for Pi-Plane</div>
            {FORM_FIELDS.map((field) => (
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
            <div className="flex items-center justify-between gap-1">
              <h4 id={`${prefix}-signup-label`} className="text-sm text-custom-text-300">
                Create accounts for new people when they sign in
              </h4>
              <Controller
                control={control}
                name={`${prefix}_ENABLE_SIGNUP`}
                render={({ field: { value, onChange } }) => (
                  <Switch
                    checked={isOn(value)}
                    onCheckedChange={() => onChange(isOn(value) ? "0" : "1")}
                    size="sm"
                    aria-labelledby={`${prefix}-signup-label`}
                  />
                )}
              />
            </div>
            <ControllerSwitch control={control} field={SYNC_SWITCH_FIELD} />
            <div className="flex flex-col gap-1 pt-4">
              <div className="flex items-center gap-4">
                <Button
                  variant="primary"
                  size="md"
                  stretch="auto"
                  onClick={(e) => void handleSubmit(onSubmit)(e)}
                  loading={isSubmitting}
                  disabled={!isDirty}
                  label={isSubmitting ? "Saving" : "Save changes"}
                />
                <Button
                  variant="secondary"
                  size="md"
                  stretch="auto"
                  nativeButton={false}
                  render={<Link href="/authentication" onClick={handleGoBack} />}
                  label="Go back"
                />
              </div>
            </div>
          </div>
          <div className="col-span-2 md:col-span-1">
            <div className="flex flex-col gap-y-4 rounded-lg bg-layer-1 px-6 pt-1.5 pb-4">
              <div className="pt-2 text-18 font-medium">Pi-Plane-provided details for {provider.name}</div>
              {SERVICE_FIELD.map((field) => (
                <CopyField key={field.key} label={field.label} url={field.url} description={field.description} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
