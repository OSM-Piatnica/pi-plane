/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

/**
 * Input Validation Utilities
 * Following OWASP Input Validation best practices using allowlist approach
 *
 * Security: Blocks injection-risk characters: < > ' " % # { } [ ] * ^ !
 * These patterns are designed to prevent XSS, SQL injection, template injection,
 * and other security vulnerabilities while maintaining good UX
 */

// =============================================================================
// VALIDATION REGEX PATTERNS
// =============================================================================

/**
 * Person Name Pattern (for first_name, last_name)
 * Allows: Unicode letters (\p{L}), spaces, hyphens, apostrophes
 * Use case: Accommodates international names like "José", "李明", "محمد", "Müller"
 * Blocks: Injection-risk characters and special symbols
 */
export const PERSON_NAME_REGEX = /^[\p{L}\s'-]+$/u;

/**
 * Display Name Pattern (for display_name, usernames)
 * Allows: Unicode letters (\p{L}), numbers (\p{N}), underscore, period, hyphen
 * Use case: International usernames like "josé_123", "李明.dev", "müller-2024"
 * Blocks: Spaces and injection-risk characters
 */
export const DISPLAY_NAME_REGEX = /^[\p{L}\p{N}_.-]+$/u;

/**
 * Company/Organization Name Pattern (for company_name, workspace names)
 * Allows: Unicode letters (\p{L}), numbers (\p{N}), spaces, underscores, hyphens
 * Use case: International business names like "Société Générale", "株式会社", "Müller GmbH"
 * Blocks: Special punctuation and injection-risk chars
 */
export const COMPANY_NAME_REGEX = /^[\p{L}\p{N}\s_-]+$/u;

/**
 * Requires at least one Unicode letter or digit in a string.
 * Used to reject symbol-only inputs like "-_________-" in workspace/company names.
 */
export const HAS_ALPHANUMERIC_REGEX = /[\p{L}\p{N}]/u;

/**
 * URL Slug Pattern (for workspace slugs, URL-safe identifiers)
 * Allows: Unicode letters (\p{L}), numbers (\p{N}), underscores, hyphens
 * Use case: International URL-safe identifiers like "josé-workspace", "李明-project"
 * Blocks: Spaces and special characters (URL encoding will handle Unicode in actual URLs)
 */
export const SLUG_REGEX = /^[\p{L}\p{N}_-]+$/u;

// =============================================================================
// VALIDATION FUNCTIONS
// =============================================================================

/**
 * Translates an i18n key. The validators run outside of components, so the caller passes its `t`.
 * The messages stay English when it is omitted.
 */
export type TValidationTranslate = (key: string, params?: Record<string, string>) => string;

// characters the allowlist rejects, shown in the "cannot contain special characters" messages
const BLOCKED_CHARS = "< > ' \" { } [ ] * ^ ! # %";

const translateValidation = (
  t: TValidationTranslate | undefined,
  key: string,
  fallback: string,
  params?: Record<string, string>
): string => (t ? t(key, params) : fallback);

/**
 * @description Validates person names (first name, last name)
 * @param {string} name - Name to validate
 * @returns {boolean | string} true if valid, error message if invalid
 * @example
 * validatePersonName("John") // returns true
 * validatePersonName("O'Brien") // returns true
 * validatePersonName("Jean-Paul") // returns true
 * validatePersonName("John<script>") // returns error message
 */
export const validatePersonName = (name: string, t?: TValidationTranslate): boolean | string => {
  if (!name || name.trim() === "") {
    return translateValidation(t, "name_is_required", "Name is required");
  }

  if (name.length > 50) {
    return translateValidation(t, "app_text.validation.name_max_length", "Name must be 50 characters or less");
  }

  if (hasInjectionRiskChars(name)) {
    return translateValidation(
      t,
      "app_text.validation.name_special_chars",
      `Names cannot contain special characters like ${BLOCKED_CHARS}`,
      { chars: BLOCKED_CHARS }
    );
  }

  if (!PERSON_NAME_REGEX.test(name)) {
    return translateValidation(
      t,
      "app_text.validation.name_invalid_chars",
      "Names can only contain letters, spaces, hyphens, and apostrophes"
    );
  }

  return true;
};

/**
 * @description Validates display names and usernames
 * @param {string} displayName - Display name to validate
 * @returns {boolean | string} true if valid, error message if invalid
 * @example
 * validateDisplayName("john_doe") // returns true
 * validateDisplayName("john.doe-123") // returns true
 * validateDisplayName("john doe") // returns error message (spaces not allowed)
 * validateDisplayName("john<>doe") // returns error message
 */
export const validateDisplayName = (displayName: string, t?: TValidationTranslate): boolean | string => {
  if (!displayName || displayName.trim() === "") {
    return true; // Display name is optional in most cases
  }

  if (displayName.length > 50) {
    return translateValidation(
      t,
      "app_text.validation.display_name_max_length",
      "Display name must be 50 characters or less"
    );
  }

  if (hasInjectionRiskChars(displayName)) {
    return translateValidation(
      t,
      "app_text.validation.display_name_special_chars",
      `Display name cannot contain special characters like ${BLOCKED_CHARS}`,
      { chars: BLOCKED_CHARS }
    );
  }

  if (!DISPLAY_NAME_REGEX.test(displayName)) {
    return translateValidation(
      t,
      "app_text.validation.display_name_invalid_chars",
      "Display name can only contain letters, numbers, periods, hyphens, and underscores"
    );
  }

  return true;
};

/**
 * @description Validates company and organization names
 * @param {string} companyName - Company name to validate
 * @param {boolean} required - Whether the field is required
 * @returns {boolean | string} true if valid, error message if invalid
 * @example
 * validateCompanyName("Acme Corp") // returns true
 * validateCompanyName("Acme_Corp-123") // returns true
 * validateCompanyName("Acme{Corp}") // returns error message
 */
export const validateCompanyName = (
  companyName: string,
  required: boolean = false,
  t?: TValidationTranslate
): boolean | string => {
  if (!companyName || companyName.trim() === "") {
    return required
      ? translateValidation(
          t,
          "templates.settings.form.publish.company_name.validation.required",
          "Company name is required"
        )
      : true;
  }

  if (companyName.length > 80) {
    return translateValidation(
      t,
      "app_text.validation.company_name_max_length",
      "Company name must be 80 characters or less"
    );
  }

  if (hasInjectionRiskChars(companyName)) {
    return translateValidation(
      t,
      "app_text.validation.company_name_special_chars",
      `Company name cannot contain special characters like ${BLOCKED_CHARS}`,
      { chars: BLOCKED_CHARS }
    );
  }

  if (!COMPANY_NAME_REGEX.test(companyName)) {
    return translateValidation(
      t,
      "app_text.validation.company_name_invalid_chars",
      "Company name can only contain letters, numbers, spaces, hyphens, and underscores"
    );
  }

  if (!HAS_ALPHANUMERIC_REGEX.test(companyName)) {
    return translateValidation(
      t,
      "app_text.validation.company_name_needs_alphanumeric",
      "Company name must contain at least one letter or number"
    );
  }

  return true;
};

/**
 * @description Validates company and organization names
 * @param {string} workspaceName - Workspace name to validate
 * @param {boolean} required - Whether the field is required
 * @returns {boolean | string} true if valid, error message if invalid
 * @example
 * validateWorkspaceName("Acme Corp") // returns true
 * validateWorkspaceName("Acme_Corp-123") // returns true
 * validateWorkspaceName("Acme{Corp}") // returns error message
 */
export const validateWorkspaceName = (
  workspaceName: string,
  required: boolean = false,
  t?: TValidationTranslate
): boolean | string => {
  if (!workspaceName || workspaceName.trim() === "") {
    return required
      ? translateValidation(t, "app_text.validation.workspace_name_required", "Workspace name is required")
      : true;
  }

  if (workspaceName.length > 80) {
    return translateValidation(
      t,
      "app_text.validation.workspace_name_max_length",
      "Workspace name must be 80 characters or less"
    );
  }

  if (hasInjectionRiskChars(workspaceName)) {
    return translateValidation(
      t,
      "app_text.validation.workspace_name_special_chars",
      `Workspace name cannot contain special characters like ${BLOCKED_CHARS}`,
      { chars: BLOCKED_CHARS }
    );
  }

  if (!COMPANY_NAME_REGEX.test(workspaceName)) {
    return translateValidation(
      t,
      "app_text.validation.workspace_name_invalid_chars",
      "Workspace name can only contain letters, numbers, spaces, hyphens, and underscores"
    );
  }

  if (!HAS_ALPHANUMERIC_REGEX.test(workspaceName)) {
    return translateValidation(
      t,
      "app_text.validation.workspace_name_needs_alphanumeric",
      "Workspace name must contain at least one letter or number"
    );
  }

  return true;
};

/**
 * @description Validates URL slugs and identifiers
 * @param {string} slug - Slug to validate
 * @returns {boolean | string} true if valid, error message if invalid
 * @example
 * validateSlug("my-workspace") // returns true
 * validateSlug("my_workspace_123") // returns true
 * validateSlug("my workspace") // returns error message (spaces not allowed)
 */
export const validateSlug = (slug: string, t?: TValidationTranslate): boolean | string => {
  if (!slug || slug.trim() === "") {
    return translateValidation(t, "app_text.validation.slug_required", "Slug is required");
  }

  if (slug.length > 48) {
    return translateValidation(t, "app_text.validation.slug_max_length", "Slug must be 48 characters or less");
  }

  if (hasInjectionRiskChars(slug)) {
    return translateValidation(
      t,
      "app_text.validation.slug_special_chars",
      `Slug cannot contain special characters like ${BLOCKED_CHARS}`,
      { chars: BLOCKED_CHARS }
    );
  }

  if (!SLUG_REGEX.test(slug)) {
    return translateValidation(
      t,
      "app_text.validation.slug_invalid_chars",
      "Slug can only contain letters, numbers, hyphens, and underscores"
    );
  }

  return true;
};

/**
 * @description Checks if a string contains any injection-risk characters
 * @param {string} input - String to check
 * @returns {boolean} true if injection-risk characters found
 * @example
 * hasInjectionRiskChars("Hello World") // returns false
 * hasInjectionRiskChars("Hello<script>") // returns true
 */
export const hasInjectionRiskChars = (input: string): boolean => {
  const injectionRiskPattern = /[<>'"{}[\]*^!#%]/;
  return injectionRiskPattern.test(input);
};
