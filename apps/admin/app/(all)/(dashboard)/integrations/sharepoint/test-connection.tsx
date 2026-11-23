/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// plane internal packages
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { TickCircleOutline, WarningCircleOutline } from "@makeplane/propel/icons";
import { InstanceService } from "@plane/services";
import type { TSharePointConnectionTest, TSharePointConnectionTestError } from "@plane/types";

type Props = {
  /** Why the test cannot run now (unsaved changes, no credentials); undefined when it can. */
  blockedReason: string | undefined;
};

type TResult =
  | { status: "success"; data: TSharePointConnectionTest }
  | { status: "error"; error: TSharePointConnectionTestError };

const SITE_URL_ID = "sharepoint-test-site-url";
const SITE_URL_DESCRIPTION_ID = "sharepoint-test-site-url-description";

const instanceService = new InstanceService();

function ConnectionTestFailure(props: { error: TSharePointConnectionTestError }) {
  const { error } = props;
  return (
    <div className="flex items-start gap-2 rounded-md border border-danger-strong bg-danger-subtle p-3">
      <WarningCircleOutline className="mt-0.5 h-4 w-4 shrink-0 text-danger-primary" aria-hidden="true" />
      <div className="space-y-1">
        <p className="text-13 font-medium text-danger-primary">{error.error}</p>
        {error.detail && <p className="text-11 break-words text-secondary">Microsoft says: {error.detail}</p>}
      </div>
    </div>
  );
}

function ConnectionTestSuccess(props: { data: TSharePointConnectionTest }) {
  const { site, libraries } = props.data;
  return (
    <div className="flex items-start gap-2 rounded-md border border-success-strong bg-success-subtle p-3">
      <TickCircleOutline className="mt-0.5 h-4 w-4 shrink-0 text-success-primary" aria-hidden="true" />
      {site ? (
        <div className="space-y-1">
          <p className="text-13 font-medium text-success-primary">
            Connected. The application can use the site “{site.name || site.web_url}”.
          </p>
          {libraries.length > 0 ? (
            <>
              <p className="text-11 text-secondary">Document libraries of the site:</p>
              <ul className="list-disc pl-5 text-13 text-primary">
                {libraries.map((library) => (
                  <li key={library.id}>{library.name || library.web_url}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-11 text-secondary">The site has no document libraries.</p>
          )}
        </div>
      ) : (
        <div className="space-y-1">
          <p className="text-13 font-medium text-success-primary">Microsoft accepted the credentials.</p>
          <p className="text-11 text-secondary">
            Enter a site URL and test again to check that the application was granted access to that site.
          </p>
        </div>
      )}
    </div>
  );
}

export function SharePointConnectionTest(props: Props) {
  const { blockedReason } = props;
  // states
  const [siteUrl, setSiteUrl] = useState("");
  const [isTesting, setIsTesting] = useState(false);
  const [result, setResult] = useState<TResult | undefined>(undefined);

  const runTest = async () => {
    setIsTesting(true);
    setResult(undefined);
    try {
      const data = await instanceService.testSharePointConnection(siteUrl.trim() || undefined);
      setResult({ status: "success", data });
    } catch (error) {
      const failure = error as Partial<TSharePointConnectionTestError> | undefined;
      setResult({
        status: "error",
        error: {
          error: failure?.error ?? "The connection could not be tested.",
          error_code: failure?.error_code ?? "unknown",
          detail: failure?.detail,
        },
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-4 border-t border-subtle pt-6">
      <div>
        <div className="pb-1 text-18 font-medium text-primary">Test connection</div>
        <div className="text-13 font-regular text-tertiary">
          Signs in to Microsoft with the saved credentials. With a site URL it also looks the site up and lists its
          document libraries.
        </div>
      </div>
      <div className="flex max-w-2xl flex-col gap-1">
        <label htmlFor={SITE_URL_ID} className="text-13 text-tertiary">
          Site URL (optional)
        </label>
        <InputGroup size="lg">
          <Input
            size="lg"
            id={SITE_URL_ID}
            name={SITE_URL_ID}
            type="url"
            value={siteUrl}
            onChange={(event) => setSiteUrl(event.target.value)}
            placeholder="https://contoso.sharepoint.com/sites/Projects"
            aria-describedby={SITE_URL_DESCRIPTION_ID}
            disabled={isTesting}
          />
        </InputGroup>
        <p id={SITE_URL_DESCRIPTION_ID} className="pt-0.5 text-11 text-tertiary">
          The address of the home page of a SharePoint site. It is used for this test only and is not saved.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          size="md"
          stretch="auto"
          onClick={() => {
            void runTest();
          }}
          loading={isTesting}
          disabled={Boolean(blockedReason) || isTesting}
          label={isTesting ? "Testing" : "Test connection"}
        />
        {blockedReason && <span className="text-11 text-tertiary">{blockedReason}</span>}
      </div>
      <div role="status" aria-live="polite">
        {result?.status === "success" && <ConnectionTestSuccess data={result.data} />}
        {result?.status === "error" && <ConnectionTestFailure error={result.error} />}
      </div>
    </div>
  );
}
