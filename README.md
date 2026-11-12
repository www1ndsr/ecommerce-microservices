# API Gateway

The API Gateway is the externally published HTTP entry point at port `8000`.
Backend API containers are reachable by their Compose service names on the
internal Docker network and are not published as host ports.

The gateway verifies Auth Service JWTs using HS256 and the same `JWT_SECRET`
as `auth-service`. It creates or forwards `X-Request-ID` and overwrites
client-supplied `X-User-ID` and `X-User-Role` headers with claims from the
verified token.

Interactive API documentation is available at `/docs` and `/redoc`. Use the
Swagger **Authorize** button for protected routes. The gateway documents
generic proxy request bodies rather than duplicating each service's schemas;
the destination service remains responsible for request validation.

`RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` configure a process-local
rate limiter keyed by client IP. This is suitable for a single Gateway
instance only. A multi-instance deployment needs a shared store such as Redis
for distributed rate limiting.

Set `JWT_SECRET` and `CORS_ORIGINS` in the environment or a local `.env` file
before deployment. The default CORS origin is `http://localhost:3000`;
wildcard origins are rejected when credentials are enabled.

## Frontend

The React/Vite application is available at `http://localhost:3000` and sends
all API requests to the Gateway at `http://localhost:8000`. Start the whole
stack with `docker compose up -d --build`. To run the frontend outside Docker,
copy `frontend/.env.example` to `frontend/.env.local`, then run `npm install`
and `npm run dev` from the `frontend` directory.