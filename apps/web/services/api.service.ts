/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
import type { AxiosInstance, AxiosRequestConfig } from "axios";
import { create } from "axios";
import { normalizeAPIRequestURL } from "@plane/services";

export abstract class APIService {
  protected baseURL: string;
  private axiosInstance: AxiosInstance;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    this.axiosInstance = create({
      baseURL,
      withCredentials: true,
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.axiosInstance.interceptors.request.use((config) => {
      try {
        if (config.url) {
          config.url = normalizeAPIRequestURL(config.url, this.baseURL);
        }
      } catch (error) {
        // Never block a request because of slash normalization — fall back to the
        // original URL and let the call proceed.
        console.warn("[APIService] Failed to normalize trailing slash:", config.url, error);
      }
      return config;
    });

    this.axiosInstance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          const url = String(error.config?.url ?? "");
          const method = String(error.config?.method ?? "get").toLowerCase();
          // GET /api/users/me/ przy braku sesji zwraca 401 — to nie jest wygaśnięcie sesji, tylko „niezalogowany”.
          const isSessionProbe = method === "get" && url.includes("/api/users/me");
          if (!isSessionProbe) {
            const currentPath = window.location.pathname;
            // Na stronie wejściowej ("/") żądanie o bieżącego użytkownika też zwraca 401, więc przekierowanie
            // "/" na "/?next_path=/" przeładowywałoby stronę w nieskończoność. Odbijamy tylko z tras prywatnych.
            if (currentPath !== "/") {
              window.location.replace(`/${currentPath ? `?next_path=${encodeURIComponent(currentPath)}` : ``}`);
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  get(url: string, params = {}, config: AxiosRequestConfig = {}) {
    return this.axiosInstance.get(url, {
      ...params,
      ...config,
    });
  }

  post(url: string, data = {}, config: AxiosRequestConfig = {}) {
    return this.axiosInstance.post(url, data, config);
  }

  put(url: string, data = {}, config: AxiosRequestConfig = {}) {
    return this.axiosInstance.put(url, data, config);
  }

  patch(url: string, data = {}, config: AxiosRequestConfig = {}) {
    return this.axiosInstance.patch(url, data, config);
  }

  delete(url: string, data?: any, config: AxiosRequestConfig = {}) {
    return this.axiosInstance.delete(url, { data, ...config });
  }

  request(config = {}) {
    return this.axiosInstance(config);
  }
}
