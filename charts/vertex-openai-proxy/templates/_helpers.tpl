{{- define "vertex-openai-proxy.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "vertex-openai-proxy.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- include "vertex-openai-proxy.name" . | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "vertex-openai-proxy.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "vertex-openai-proxy.labels" -}}
helm.sh/chart: {{ include "vertex-openai-proxy.chart" . }}
app.kubernetes.io/name: {{ include "vertex-openai-proxy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "vertex-openai-proxy.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vertex-openai-proxy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "vertex-openai-proxy.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "vertex-openai-proxy.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "vertex-openai-proxy.secretName" -}}
{{- if .Values.auth.existingSecret -}}
{{- .Values.auth.existingSecret -}}
{{- else -}}
{{- printf "%s-auth" (include "vertex-openai-proxy.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "vertex-openai-proxy.selectedProfile" -}}
{{- $profileName := default "balanced" .Values.profile -}}
{{- $profile := index .Values.profiles $profileName -}}
{{- if not $profile -}}
{{- fail (printf "Unknown profile %q. Expected one of: small, balanced, heavy." $profileName) -}}
{{- end -}}
{{- toYaml $profile -}}
{{- end -}}

{{- define "vertex-openai-proxy.resources" -}}
{{- $profile := include "vertex-openai-proxy.selectedProfile" . | fromYaml -}}
{{- if .Values.resources -}}
{{- toYaml .Values.resources -}}
{{- else -}}
{{- toYaml $profile.resources -}}
{{- end -}}
{{- end -}}

{{- define "vertex-openai-proxy.embeddingMaxConcurrency" -}}
{{- $profile := include "vertex-openai-proxy.selectedProfile" . | fromYaml -}}
{{- if .Values.runtime.embedding.maxConcurrency -}}
{{- .Values.runtime.embedding.maxConcurrency -}}
{{- else -}}
{{- $profile.runtime.embeddingMaxConcurrency -}}
{{- end -}}
{{- end -}}
