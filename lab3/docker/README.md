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
