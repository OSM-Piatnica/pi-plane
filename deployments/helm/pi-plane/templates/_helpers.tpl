{{- /*
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
*/ -}}

{{- define "pi-plane.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "pi-plane.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "pi-plane.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Labels shared by every object */}}
{{- define "pi-plane.labels" -}}
helm.sh/chart: {{ include "pi-plane.chart" . }}
app.kubernetes.io/name: {{ include "pi-plane.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: pi-plane
{{- end -}}

{{/* Selector labels of one component: call with (dict "root" . "component" "api") */}}
{{- define "pi-plane.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pi-plane.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Name of one component's objects: call with (dict "root" . "component" "api") */}}
{{- define "pi-plane.componentName" -}}
{{- printf "%s-%s" (include "pi-plane.fullname" .root) .component | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Image of an application component: call with (dict "root" . "component" "api") */}}
{{- define "pi-plane.image" -}}
{{- printf "%s-%s:%s" .root.Values.image.repository .component (.root.Values.image.tag | default .root.Chart.AppVersion) -}}
{{- end -}}

{{/* The Secret holding the generated or operator-supplied credentials */}}
{{- define "pi-plane.secretName" -}}
{{- default (printf "%s-credentials" (include "pi-plane.fullname" .)) .Values.secrets.existingSecret -}}
{{- end -}}

{{- define "pi-plane.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "pi-plane.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Host of the public URL, e.g. plane.example.com */}}
{{- define "pi-plane.host" -}}
{{- (urlParse (required "publicUrl is required, e.g. https://plane.example.com" .Values.publicUrl)).host -}}
{{- end -}}

{{/* "1" when the public URL is https: presigned upload URLs then use https too */}}
{{- define "pi-plane.sslTermination" -}}
{{- if hasPrefix "https://" .Values.publicUrl -}}1{{- else -}}0{{- end -}}
{{- end -}}

{{/* In-cluster names of the bundled stores */}}
{{- define "pi-plane.postgresHost" -}}{{ include "pi-plane.componentName" (dict "root" . "component" "postgres") }}{{- end -}}
{{- define "pi-plane.valkeyHost" -}}{{ include "pi-plane.componentName" (dict "root" . "component" "valkey") }}{{- end -}}
{{- define "pi-plane.rabbitmqHost" -}}{{ include "pi-plane.componentName" (dict "root" . "component" "rabbitmq") }}{{- end -}}
{{- define "pi-plane.minioHost" -}}{{ include "pi-plane.componentName" (dict "root" . "component" "minio") }}{{- end -}}

{{/* An env var that is either a literal URL or read from a Secret: call with (dict "name" "REDIS_URL" "external" .Values.valkey.external) */}}
{{- define "pi-plane.externalUrlEnv" -}}
- name: {{ .name }}
{{- if .external.urlSecret.name }}
  valueFrom:
    secretKeyRef:
      name: {{ .external.urlSecret.name }}
      key: {{ required (printf "%s: urlSecret.key is required with urlSecret.name" .name) .external.urlSecret.key }}
{{- else }}
  value: {{ required (printf "%s: set the external url or urlSecret (the bundled service is off)" .name) .external.url | quote }}
{{- end }}
{{- end -}}

{{/* Credentials and connection strings of every backend container (api, worker, beat, migrator) */}}
{{- define "pi-plane.backendEnv" -}}
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pi-plane.secretName" . }}
      key: SECRET_KEY
- name: LIVE_SERVER_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pi-plane.secretName" . }}
      key: LIVE_SERVER_SECRET_KEY
{{- if .Values.postgresql.enabled }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "pi-plane.secretName" . }}
      key: POSTGRES_PASSWORD
- name: DATABASE_URL
  value: {{ printf "postgresql://%s:$(POSTGRES_PASSWORD)@%s:5432/%s" .Values.postgresql.username (include "pi-plane.postgresHost" .) .Values.postgresql.database | quote }}
{{- else }}
{{ include "pi-plane.externalUrlEnv" (dict "name" "DATABASE_URL" "external" .Values.postgresql.external) }}
{{- end }}
{{- if .Values.valkey.enabled }}
- name: REDIS_URL
  value: {{ printf "redis://%s:6379/" (include "pi-plane.valkeyHost" .) | quote }}
{{- else }}
{{ include "pi-plane.externalUrlEnv" (dict "name" "REDIS_URL" "external" .Values.valkey.external) }}
{{- end }}
{{- if .Values.rabbitmq.enabled }}
- name: RABBITMQ_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "pi-plane.secretName" . }}
      key: RABBITMQ_PASSWORD
- name: AMQP_URL
  value: {{ printf "amqp://%s:$(RABBITMQ_PASSWORD)@%s:5672/%s" .Values.rabbitmq.username (include "pi-plane.rabbitmqHost" .) .Values.rabbitmq.vhost | quote }}
{{- else }}
{{ include "pi-plane.externalUrlEnv" (dict "name" "AMQP_URL" "external" .Values.rabbitmq.external) }}
{{- end }}
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: {{ include "pi-plane.secretName" . }}
      key: AWS_ACCESS_KEY_ID
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pi-plane.secretName" . }}
      key: AWS_SECRET_ACCESS_KEY
{{- end -}}

{{/* Container security context of the application containers (the images run as root today, so no runAsNonRoot) */}}
{{- define "pi-plane.containerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{/* Scheduling fields of a component: call with its values (nodeSelector, tolerations, affinity) */}}
{{- define "pi-plane.scheduling" -}}
{{- with .nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}
