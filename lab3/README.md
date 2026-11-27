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
    if ($name -eq 'gateway' -or $name -eq 'frontend') { $context = "./$name" }
    else { $context = "./services/$name" }
    minikube image build $context --tag "shop/${name}:1.0" --file Dockerfile
    if ($LASTEXITCODE -ne 0) { throw "Image build failed: shop/${name}:1.0" }
}
.\lab3\deploy.ps1
```

Minikube 1.39 uses containerd by default; its `docker-env` path reports
`SSH_AGENT_START` on this Windows setup. `minikube image build` builds the same
Compose-tagged images directly into containerd, where Kubernetes can use them
with `imagePullPolicy: IfNotPresent`.

Перед первым запуском создайте `.env` из `.env.example`, оставьте имена
пользователей `app` и `shop` либо задайте свои (латинские буквы, цифры и `_`,
начиная с буквы или `_`) и заполните три пустых секрета.
`deploy.ps1` берёт `POSTGRES_USER` и `RABBITMQ_USER` из `.env` и
синхронизирует их с ConfigMap `app-config`; пароли и JWT-ключ попадают в Secret
`app-secrets`, который создаётся только при отсутствии. Настоящие значения не
хранятся в Git. Пример структуры Secret находится в
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

## Дополнение: состав и эксплуатация

### Требования и расположение файлов

Для локального запуска нужны Docker Desktop с запущенным Docker Engine,
`kubectl`, Minikube и PowerShell. Манифесты находятся в `lab3/k8s/`:
`namespace.yaml` создаёт namespace `shop`, `configmaps/app-config.yaml`
содержит настройки приложения, `secrets/secret.example.yaml` показывает
структуру Secret без настоящих значений, `infrastructure/` описывает базы и
RabbitMQ, `services/` — сетевые Service-объекты, а `deployments/` — приложение.
Скрипт `lab3/deploy.ps1` применяет ресурсы в этом порядке и в конце показывает
состояние Pod'ов, Service и Deployment.

Перед первым запуском скопируйте `.env.example` в `.env` и задайте значения
`POSTGRES_PASSWORD`, `JWT_SECRET` и `RABBITMQ_PASS`; в примере уже стоят
несекретные имена пользователей `app` и `shop`. Скрипт читает их из `.env` и
обновляет соответствующие ключи ConfigMap, поэтому Compose и Kubernetes
используют одинаковые имена. При первом запуске `deploy.ps1` создаёт Secret
`app-secrets` только из пароля PostgreSQL, JWT-ключа и пароля RabbitMQ; уже
созданный Secret скрипт не перезаписывает. Не добавляйте `.env` или
`lab3/k8s/secrets/secret.yaml` в Git. Для уже созданного кластера не меняйте
имя пользователя или пароль базы/брокера без согласованной ротации учётных
данных: PostgreSQL и RabbitMQ сохраняют первоначальные credentials в PVC.

### Сервисы приложения

Порты ниже — внутренние порты контейнеров. Gateway и frontend доступны снаружи
через NodePort; остальные сервисы доступны внутри namespace через DNS-имена.
Backend liveness/readiness используют `/health` и `/ready` на порту `8000`;
frontend проверяется запросом `/` на порту `8080`.

| Deployment | Порт контейнера | Реплики по умолчанию | Liveness / readiness |
|---|---:|---:|---|
| auth-service | 8000 | 1 | `/health` / `/ready` |
| user-service | 8000 | 1 | `/health` / `/ready` |
| product-service | 8000 | 1 | `/health` / `/ready` |
| cart-service | 8000 | 1 | `/health` / `/ready` |
| order-service | 8000 | 2 | `/health` / `/ready` |
| payment-service | 8000 | 1 | `/health` / `/ready` |
| notification-service | 8000 | 1 | `/health` / `/ready` |
| inventory-service | 8000 | 1 | `/health` / `/ready` |
| review-service | 8000 | 1 | `/health` / `/ready` |
| promotion-service | 8000 | 1 | `/health` / `/ready` |
| shipping-service | 8000 | 1 | `/health` / `/ready` |
| wishlist-service | 8000 | 1 | `/health` / `/ready` |
| gateway | 8000 | 2 | `/health` / `/ready` |
| frontend | 8080 | 1 | `/` / `/` |

У gateway NodePort `30000`, у frontend — `30080`. Если NodePort недоступен в
Minikube с Docker на Windows, откройте два PowerShell-окна и запустите:

```powershell
kubectl port-forward -n shop svc/gateway 8000:8000
kubectl port-forward -n shop svc/frontend 3000:8080
```

Тогда frontend будет доступен по адресу `http://localhost:3000/`, а API —
через `http://localhost:8000/`. Frontend обращается к API по относительному
пути `/api`, который проксируется через Nginx в Gateway.

### Ресурсы и переключение между Compose и Minikube

Для контейнеров приложения заданы requests `100m` CPU и `128Mi` памяти и
limits `500m` CPU и `512Mi`. Для StatefulSet заданы requests `50m` CPU и
`128Mi`, limits `300m` CPU и `384Mi`; данные каждой базы/брокера хранятся в
отдельном PVC размером `1Gi`. Readiness не направляет запросы в Pod до
готовности его зависимостей, liveness перезапускает не отвечающий процесс,
startup probe даёт хранилищам время на первоначальный запуск.

Compose-стек и Minikube вместе требуют заметно больше памяти. Чтобы освободить
ресурсы перед запуском Minikube, остановите Compose-контейнеры без удаления:

```powershell
docker compose stop
minikube start --driver=docker --cpus=4 --memory=6144
```

Для возврата к Compose остановите Minikube (`minikube stop`), затем выполните
`docker compose start`. Команды `down -v` для переключения не нужны: они
удаляют контейнеры и тома с данными.

### Сохранение демонстрации

Чтобы сохранить вывод команд для отчёта, начните запись PowerShell-транскрипта
из корня проекта, выполните демонстрацию и завершите запись:

```powershell
Start-Transcript -Path .\lab3\demo-output.txt
kubectl get pods -n shop
kubectl get services -n shop
kubectl get deployments -n shop
$pod = kubectl get pods -n shop -l app=order-service -o jsonpath='{.items[0].metadata.name}'
kubectl logs $pod -n shop --tail=20
kubectl scale deployment order-service --replicas=3 -n shop
kubectl rollout status deployment/order-service -n shop
kubectl get pods -n shop -l app=order-service
kubectl scale deployment order-service --replicas=2 -n shop
$pod = kubectl get pods -n shop -l app=order-service -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod -n shop
kubectl get pods -n shop -l app=order-service
Stop-Transcript
```

После пересоздания Pod проверьте API и frontend по адресам из раздела выше.
Проверьте содержимое `lab3/demo-output.txt` перед передачей отчёта: запись
должна показывать успешное масштабирование и появление нового Pod.

### Частые проблемы

- **Pod остаётся Pending или перезапускается из-за памяти.** Остановите
  Compose-компоненты командой `docker compose stop`; проверьте доступную память
  Docker Desktop и `kubectl describe pod -n shop <имя-pod>`.
- **ImagePullBackOff.** Убедитесь, что образ `shop/<сервис>:1.0` загружен в
  runtime Minikube (`minikube image ls | Select-String shop/`). Загрузите
  отсутствующий образ через `minikube image load shop/<сервис>:1.0` после
  подготовки этого тега.
- **Сервис не Ready.** Посмотрите `kubectl describe pod` и `kubectl logs`; при
  первом старте базы и RabbitMQ могут потребовать дополнительного времени.
- **Secret отсутствует.** Проверьте наличие `.env` с пятью непустыми ключами и
  повторно запустите `lab3/deploy.ps1`. Если Secret уже существует, скрипт его
  не перезаписывает. Перед изменением пароля нужно обновить credentials в самой
  базе/брокере и Kubernetes Secret; изменение только `.env` недостаточно.

Для RabbitMQ установлены отдельные ресурсы: request `250m` CPU и `128Mi`,
limit `1` CPU и `512Mi`; timeout всех трёх probes — `20` секунд. Это даёт
брокеру время на запуск и диагностику в локальном Minikube, где одновременная
нагрузка баз данных и сервисов может замедлить `rabbitmq-diagnostics`.
Для MongoDB request составляет `250m` CPU и `128Mi`, limit — `1` CPU и
`384Mi`; timeout её startup, liveness и readiness probes также равен
`20` секундам, чтобы короткий запуск `mongosh` не вызывал перезапуск базы
при высокой нагрузке узла.

## Соответствие заданию

| Требование методички | Как выполнено | Файл |
|---|---|---|
| Dockerfile | Для backend и Gateway образы запускаются от `appuser`; зависимости копируются и устанавливаются до исходного кода для кэширования слоёв. Frontend собирается в отдельной build-стадии и запускается непривилегированным Nginx. | [`services/*/Dockerfile`](../services/), [`gateway/Dockerfile`](../gateway/Dockerfile), [`frontend/Dockerfile`](../frontend/Dockerfile) |
| `.dockerignore` | Build context исключает `.git`, локальные env-файлы, кэш и ненужные каталоги. | [`services/*/.dockerignore`](../services/), [`gateway/.dockerignore`](../gateway/.dockerignore), [`frontend/.dockerignore`](../frontend/.dockerignore) |
| Docker Compose | Файл описывает запуск инфраструктуры и приложений; `docker compose config --quiet` проходит, у каждого build-сервиса назначен образ `shop/<имя>:1.0`. | [`docker-compose.yml`](../docker-compose.yml) |
| Deployment | Есть Deployment для 12 backend-сервисов, Gateway и frontend; описаны образ, реплики, порт, env, ресурсы и пробы. | [`k8s/deployments/`](k8s/deployments/) |
| Service | Внутренние сервисы доступны по Kubernetes DNS; Gateway и frontend также имеют NodePort. | [`k8s/services/`](k8s/services/) |
| ConfigMap | Обычные настройки, включая `LOG_LEVEL` и адреса сервисов, вынесены в `app-config`. | [`k8s/configmaps/app-config.yaml`](k8s/configmaps/app-config.yaml) |
| Secret | `deploy.ps1` при первом развёртывании создаёт `app-secrets` из корневого `.env`; шаблон не содержит значений, локальный Secret исключён из Git. | [`k8s/secrets/secret.example.yaml`](k8s/secrets/secret.example.yaml), [`deploy.ps1`](deploy.ps1), [`.gitignore`](../.gitignore) |
| Health checks | Backend и Gateway проверяются по `/health` и `/ready`, frontend — по `/`. | [`k8s/deployments/`](k8s/deployments/), [`services/*/app/main.py`](../services/) |
| Resources | Для приложений и хранилищ заданы requests и limits; для MongoDB и RabbitMQ установлены более длинные probe timeout для локального Minikube. | [`k8s/deployments/`](k8s/deployments/), [`k8s/infrastructure/`](k8s/infrastructure/) |
| Масштабирование | Order Service масштабировался до 3 реплик, после демонстрации возвращён к 2. | [`demo-output.txt`](demo-output.txt), [`k8s/deployments/order-service.yaml`](k8s/deployments/order-service.yaml) |
| Восстановление Pod | Удаление одного Pod Order Service показало, что Deployment автоматически создаёт замену. | [`demo-output.txt`](demo-output.txt) |
| Запуск в Minikube | `deploy.ps1` применяет namespace, ConfigMap, Secret, инфраструктуру, Service и Deployment, ожидая готовности ресурсов. | [`deploy.ps1`](deploy.ps1), [`k8s/`](k8s/) |

## Шпаргалка для защиты

### Запуск после перезагрузки компьютера

Убедитесь, что Docker Desktop запущен, затем из корня репозитория выполните:

```powershell
minikube start --driver=docker --cpus=4 --memory=6144
kubectl config current-context
kubectl get pods -n shop
```

Если профиль Minikube уже создан, команда `minikube start` запускает его снова.
Проверьте, что контекст — `minikube`, а Pod'ы перешли в `Running` и `Ready`.

### Открытие frontend и Gateway

В отдельных окнах PowerShell оставьте работающими port-forward процессы:

```powershell
kubectl port-forward -n shop svc/frontend 3000:8080
```

```powershell
kubectl port-forward -n shop svc/gateway 8000:8000
```

Frontend откроется на `http://localhost:3000/`; Gateway — на
`http://localhost:8000/`, его Swagger UI — `/docs`.

### Команды демонстрации

```powershell
kubectl get pods -n shop
kubectl get services -n shop
kubectl get deployments -n shop
kubectl logs deployment/order-service -n shop --tail=20
kubectl scale deployment order-service --replicas=3 -n shop
kubectl rollout status deployment/order-service -n shop
kubectl get pods -n shop -l app=order-service
kubectl scale deployment order-service --replicas=2 -n shop
$pod = kubectl get pods -n shop -l app=order-service -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod -n shop
kubectl get pods -n shop -l app=order-service
```

После удаления Pod Deployment сам создаёт замену. Результаты API-сценария,
масштабирования и восстановления сохранены в [`demo-output.txt`](demo-output.txt).

### Compose и Minikube

Оба стека запускают много контейнеров и вместе потребляют больше памяти. Для
освобождения ресурсов перед Minikube остановите Compose без удаления данных:
`docker compose stop`. Чтобы вернуться к Compose, выполните `minikube stop`,
затем `docker compose start`. Не используйте `docker compose down -v` для
переключения: эта команда удаляет тома с данными.
