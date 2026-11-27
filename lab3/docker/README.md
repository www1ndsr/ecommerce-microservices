# Docker-часть

Лабораторная работа №2 уже содержит Dockerfile каждого backend-сервиса,
gateway и multi-stage frontend. В корневом `docker-compose.yml` каждому build
назначен стабильный тег `shop/<service>:1.0`; Kubernetes-манифесты используют
эти же образы с `imagePullPolicy: IfNotPresent`.

Исходные Dockerfile находятся в [`services/`](../../services/),
[`gateway/`](../../gateway/) и [`frontend/`](../../frontend/). Образы для
Minikube собираются через `minikube image build`, чтобы помещать их
непосредственно в containerd. На кластере с Docker runtime допустима сборка
через `minikube docker-env` и `docker compose build`.

## Дополнение: устройство Docker-сборки

Backend-образы основаны на `python:3.12-slim`. Сначала копируется файл
зависимостей и устанавливаются пакеты, затем добавляется исходный код — так
изменения приложения не требуют повторно загружать неизменившиеся зависимости.
Backend-процессы работают от непривилегированного пользователя `appuser`.
Frontend собирается в отдельной Node.js-стадии, а готовые статические файлы
попадают в непривилегированный Nginx-образ.

Файлы `.dockerignore` исключают из build context локальные виртуальные среды,
кэш, `.git`, тесты и локальные env-файлы. Это сокращает контекст сборки и не
передаёт локальные секреты в Docker build. Смотри [Dockerfile сервисов](../../services/),
[Dockerfile Gateway](../../gateway/Dockerfile),
[Dockerfile frontend](../../frontend/Dockerfile) и соответствующие файлы
`.dockerignore` в каталогах приложений.

Корневой [`docker-compose.yml`](../../docker-compose.yml) связывает сборку
приложений с тегами `shop/<service>:1.0` и задаёт адреса зависимостей. Для
локального Compose создайте `.env` на основе [`.env.example`](../../.env.example).
Там заданы имена пользователей `app` и `shop`; заполните три пустых значения
паролей/JWT. Те же имена использует Kubernetes: `lab3/deploy.ps1` переносит их
из `.env` в ConfigMap. `.env` не хранится в Git; не помещайте реальные пароли
и JWT-ключи в Dockerfile, Compose-файл или Kubernetes-манифесты.

Compose и Minikube одновременно потребляют много памяти. Перед запуском
Minikube остановите Compose-компоненты без удаления данных командой
`docker compose stop`; чтобы вернуться, выполните `minikube stop`, затем
`docker compose start`.
