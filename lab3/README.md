# Лабораторная работа №3 — Kubernetes

Манифесты в `k8s/` разворачивают namespace `shop`, 13 StatefulSet-хранилищ и
брокеров, а также 12 backend-сервисов, gateway и frontend. Приложения используют
Kubernetes DNS-имена Service; для внешнего доступа созданы NodePort gateway
(`30000`) и frontend (`30080`).

## Запуск в Windows PowerShell

Из корня репозитория запустите Minikube и соберите все Compose-образы внутри его
container runtime:

```powershell
minikube start --driver=docker --cpus=4 --memory=6144
$services = @('auth-service','user-service','product-service','cart-service','order-service','payment-service','notification-service','inventory-service','review-service','promotion-service','shipping-service','wishlist-service','gateway','frontend')
foreach ($name in $services) {
    if ($name -eq 'gateway' -or $name -eq 'frontend') { $context = ".\$name" }
    else { $context = ".\services\$name" }
    minikube image build --tag "shop/${name}:1.0" --file "$context\Dockerfile" $context
    if ($LASTEXITCODE -ne 0) { throw "Image build failed: shop/${name}:1.0" }
}
.\lab3\deploy.ps1
```

Minikube 1.39 uses containerd by default; its `docker-env` path reports
`SSH_AGENT_START` on this Windows setup. `minikube image build` builds the same
Compose-tagged images directly into containerd, where Kubernetes can use them
with `imagePullPolicy: IfNotPresent`.

`.env` в корне должен содержать `POSTGRES_PASSWORD`, `JWT_SECRET` и
`RABBITMQ_PASS`; скрипт создаёт из него Secret `app-secrets`, если Secret ещё не
существует. Значения секретов не хранятся в Git. Пример формата находится в
`k8s/secrets/secret.example.yaml`.

Открыть frontend:

```powershell
minikube service frontend -n shop --url
```

## Демонстрация

```powershell
kubectl get pods -n shop
kubectl get services -n shop
kubectl get deployments -n shop
$pod = kubectl get pods -n shop -l app=order-service -o jsonpath='{.items[0].metadata.name}'
kubectl logs $pod -n shop --tail=30
```

Для API запросов через gateway можно использовать `http://$(minikube ip):30000`.
На Windows Docker driver, если NodePort недоступен напрямую, запустите
`minikube service gateway -n shop --url` и используйте напечатанный адрес.
Следующий сценарий выполняет регистрацию, вход, добавление товара `1` в
корзину и создание заказа:

```powershell
$gateway = "http://$(minikube ip):30000"
$email = "lab3-$([guid]::NewGuid().ToString('N'))@example.test"
$password = "Lab3-$([guid]::NewGuid().ToString('N'))"
$credentials = @{ email = $email; password = $password } | ConvertTo-Json -Compress
Invoke-RestMethod -Method Post "$gateway/api/auth/register" -ContentType 'application/json' -Body $credentials
$login = Invoke-RestMethod -Method Post "$gateway/api/auth/login" -ContentType 'application/json' -Body $credentials
$headers = @{ Authorization = "Bearer $($login.access_token)" }
$cart = @{ product_id = 1; quantity = 1 } | ConvertTo-Json -Compress
Invoke-RestMethod -Method Post "$gateway/api/cart/items" -Headers $headers -ContentType 'application/json' -Body $cart
Invoke-RestMethod -Method Post "$gateway/api/orders" -Headers $headers
```

Масштабирование Order Service и проверка самовосстановления Pod:

```powershell
kubectl scale deployment order-service --replicas=3 -n shop
kubectl rollout status deployment/order-service -n shop
$pod = kubectl get pods -n shop -l app=order-service -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod -n shop
kubectl get pods -n shop -l app=order-service --watch
```

## Ресурсы и пробы

Приложения запрашивают `100m` CPU и `128Mi` памяти (лимиты `500m`/`512Mi`);
StatefulSet-хранилища — `50m`/`128Mi` (лимиты `300m`/`384Mi`) и отдельный PVC
`1Gi`. Небольшие requests позволяют разместить лабораторный стек в Minikube,
а limits ограничивают влияние контейнеров на узел.

Backend liveness проверяет `/health`, readiness — `/ready` на порту `8000`.
Readiness исключает Pod из Service endpoints, пока его зависимости не готовы;
liveness перезапускает зависший процесс. Frontend проверяется на `/` порта
`8080`. StatefulSet использует нативные readiness/liveness/startup probes:
`pg_isready`, `redis-cli ping`, `mongosh` ping и `rabbitmq-diagnostics`.
