{{- /*
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
*/ -}}

{{/*
The public routes, most specific first, as a list of {path, service, port}. The same list feeds the Ingress and
the Gateway API routes, so the two cannot drift. The prefixes are the ones the all-in-one proxy (Caddyfile.ce)
sends to each application; the bucket path is only routed when the bundled object storage is used, because browsers
upload to it through presigned URLs.
*/}}
{{- define "pi-plane.routes" -}}
- { path: /spaces, component: space, port: 3000 }
- { path: /god-mode, component: admin, port: 3000 }
- { path: /live, component: live, port: 3000 }
- { path: /api, component: api, port: 8000 }
- { path: /auth, component: api, port: 8000 }
- { path: /static, component: api, port: 8000 }
{{- if .Values.objectStorage.bundled.enabled }}
- { path: {{ printf "/%s" .Values.objectStorage.bucket }}, component: minio, port: 9000 }
{{- end }}
- { path: /, component: web, port: 3000 }
{{- end -}}
