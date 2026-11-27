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

function Read-EnvFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required environment file not found: $Path. Copy .env.example to .env and fill in the values."
    }

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $entry = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($entry) -or $entry.StartsWith('#')) {
            continue
        }
        if ($entry.StartsWith('export ')) {
            $entry = $entry.Substring(7).TrimStart()
        }

        $separator = $entry.IndexOf('=')
        if ($separator -lt 1) {
            continue
        }

        $name = $entry.Substring(0, $separator).Trim()
        $value = $entry.Substring($separator + 1).Trim()
        if ($value.Length -ge 2 -and
            (($value.StartsWith('"') -and $value.EndsWith('"')) -or
             ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$name] = $value
    }

    $requiredKeys = @(
        'POSTGRES_USER', 'POSTGRES_PASSWORD', 'JWT_SECRET',
        'RABBITMQ_USER', 'RABBITMQ_PASS'
    )
    foreach ($key in $requiredKeys) {
        if (-not $values.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($values[$key])) {
            throw "Environment variable $key is missing or empty in $Path. Fill it before deployment."
        }
    }
    foreach ($key in @('POSTGRES_USER', 'RABBITMQ_USER')) {
        if ($values[$key] -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
            throw "$key must contain only letters, digits and underscores, and start with a letter or underscore."
        }
    }

    return $values
}

$environment = Read-EnvFile -Path $envFile

$context = & kubectl config current-context
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read the current kubectl context'
}
if (($context -join '').Trim() -ne 'minikube') {
    throw "Expected kubectl context 'minikube', got '$($context -join '')'"
}
Invoke-Kubectl @('apply', '-f', (Join-Path $k8sRoot 'namespace.yaml'))
Invoke-Kubectl @('apply', '-f', (Join-Path $k8sRoot 'configmaps'))

# Keep the Kubernetes usernames aligned with the same .env used by Compose.
$configMapPatch = @{
    data = @{
        POSTGRES_USER = $environment['POSTGRES_USER']
        RABBITMQ_USER = $environment['RABBITMQ_USER']
    }
} | ConvertTo-Json -Compress
$configPatchFile = Join-Path ([System.IO.Path]::GetTempPath()) "shop-config-$([guid]::NewGuid().ToString('N')).json"
[System.IO.File]::WriteAllText(
    $configPatchFile,
    $configMapPatch,
    [System.Text.UTF8Encoding]::new($false)
)
try {
    Invoke-Kubectl @(
        'patch', 'configmap/app-config', '-n', 'shop',
        '--type', 'merge', '--patch-file', $configPatchFile
    )
}
finally {
    Remove-Item -LiteralPath $configPatchFile -Force -ErrorAction SilentlyContinue
}

$existingSecret = & kubectl get secret app-secrets -n shop --ignore-not-found -o name
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to check whether app-secrets already exists'
}
if ([string]::IsNullOrWhiteSpace(($existingSecret -join '').Trim())) {
    $secretEnvFile = Join-Path ([System.IO.Path]::GetTempPath()) "shop-secrets-$([guid]::NewGuid().ToString('N')).env"
    $secretContent = @(
        "POSTGRES_PASSWORD=$($environment['POSTGRES_PASSWORD'])"
        "JWT_SECRET=$($environment['JWT_SECRET'])"
        "RABBITMQ_PASS=$($environment['RABBITMQ_PASS'])"
    ) -join "`n"
    [System.IO.File]::WriteAllText(
        $secretEnvFile,
        $secretContent,
        [System.Text.UTF8Encoding]::new($false)
    )
    try {
        Invoke-Kubectl @(
            'create', 'secret', 'generic', 'app-secrets', '-n', 'shop',
            "--from-env-file=$secretEnvFile"
        )
    }
    finally {
        Remove-Item -LiteralPath $secretEnvFile -Force -ErrorAction SilentlyContinue
    }
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
