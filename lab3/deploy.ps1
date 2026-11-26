$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$k8sRoot = Join-Path $PSScriptRoot 'k8s'
$envFile = Join-Path $projectRoot '.env'

function Invoke-Kubectl {
    param([string[]]$KubectlArgs)

    & kubectl @KubectlArgs
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl $($KubectlArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$context = & kubectl config current-context
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read the current kubectl context'
}
if (($context -join '').Trim() -ne 'minikube') {
    throw "Expected kubectl context 'minikube', got '$($context -join '')'"
}
Invoke-Kubectl @('apply', '-f', (Join-Path $k8sRoot 'namespace.yaml'))
Invoke-Kubectl @('apply', '-f', (Join-Path $k8sRoot 'configmaps'))

$existingSecret = & kubectl get secret app-secrets -n shop --ignore-not-found -o name
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to check whether app-secrets already exists'
}
if ([string]::IsNullOrWhiteSpace(($existingSecret -join '').Trim())) {
    if (-not (Test-Path -LiteralPath $envFile)) {
        throw "Required environment file not found: $envFile"
    }
    Invoke-Kubectl @(
        'create', 'secret', 'generic', 'app-secrets', '-n', 'shop',
        "--from-env-file=$envFile"
    )
}

$infrastructurePath = Join-Path $k8sRoot 'infrastructure'
Invoke-Kubectl @('apply', '-f', $infrastructurePath)

$infrastructure = @(
    'auth-db', 'user-db', 'product-db', 'order-db', 'payment-db',
    'inventory-db', 'review-db', 'promotion-db', 'shipping-db',
    'wishlist-db', 'notification-db', 'cart-db', 'rabbitmq'
)
foreach ($name in $infrastructure) {
    Invoke-Kubectl @(
        'rollout', 'status', "statefulset/$name", '-n', 'shop', '--timeout=600s'
    )
}
Invoke-Kubectl @(
    'wait', '--for=condition=Ready', 'pod',
    '--selector=app.kubernetes.io/component=infrastructure',
    '-n', 'shop', '--timeout=600s'
)

Invoke-Kubectl @('apply', '-f', (Join-Path $k8sRoot 'services'))
Invoke-Kubectl @('apply', '-f', (Join-Path $k8sRoot 'deployments'))

$deployments = @(
    'auth-service', 'user-service', 'product-service', 'cart-service',
    'order-service', 'payment-service', 'notification-service',
    'inventory-service', 'review-service', 'promotion-service',
    'shipping-service', 'wishlist-service', 'gateway', 'frontend'
)
foreach ($name in $deployments) {
    Invoke-Kubectl @(
        'rollout', 'status', "deployment/$name", '-n', 'shop', '--timeout=600s'
    )
}
Invoke-Kubectl @(
    'wait', '--for=condition=Ready', 'pod',
    '--selector=app.kubernetes.io/part-of=shop',
    '-n', 'shop', '--timeout=600s'
)
Invoke-Kubectl @('get', 'pods,svc,deploy', '-n', 'shop')
