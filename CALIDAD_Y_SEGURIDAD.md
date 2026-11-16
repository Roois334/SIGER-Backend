# Calidad y seguridad del BACKEND

## 1. La contrasena y la red (HTTPS)

La contrasena **siempre** viaja en el cuerpo del `POST /api/auth/login`; en cualquier sitio web es asi. Lo que la protege es que el canal este **cifrado (HTTPS)**. Cifrarla o hashearla en el navegador *no* ayuda (el hash pasaria a ser la contrasena). Lo que hace el codigo ahora:

| Medida | Donde |
|---|---|
| Si el proxy de Azure avisa que el cliente uso **HTTP**: `GET` se redirige a HTTPS y los `POST` (login, cambio de contrasena) **se rechazan con 426 sin procesarlos** | `utilities/seguridad.py` |
| Cabecera **HSTS** (el navegador usa siempre HTTPS con el sitio) | `utilities/seguridad.py` |
| Respuestas de `/api/auth/*` y `/api/usuarios/me*` con `Cache-Control: no-store` | `app.py` |
| El login rechaza contrasenas no-texto o mayores de 128 caracteres sin calcular el hash | `services/auth_service.py` |
| Contrasenas guardadas con hash (`werkzeug`), enlaces de recuperacion guardados solo como hash SHA-256 | ya existia |

**En Azure (una sola vez, por cada app):**
```bash
az webapp update -g siger-rg -n siger-backend-2716 --https-only true
az webapp config set -g siger-rg -n siger-backend-2716 --min-tls-version 1.2
```
Y en el frontend: `BACKEND_URL=https://siger-backend-2716.azurewebsites.net` y `FRONTEND_URL=https://siger-frontend-2716.azurewebsites.net`.
En local no cambia nada (sin proxy no hay bloqueo). `FORCE_HTTPS=0` lo desactiva solo para depurar.

## 2. Pruebas unitarias

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest --cov --cov-config=.coveragerc --cov-report=term-missing
```
- Usan **SQLite en memoria**: no tocan Azure ni PostgreSQL y no envian correos.
- `.coveragerc` exige **70 %** como minimo (`fail_under`) y mide solo el codigo de la aplicacion (no `tests/`, `venv/` ni los scripts `parche_*.py`, que ni siquiera estan en Git).
- Se crean `coverage.xml` (para SonarQube) y `junit.xml`.

## 3. CI (GitHub Actions)

`.github/workflows/ci.yml` corre pruebas + cobertura + SonarQube en cada Pull Request a `main` y en cada push a otras ramas.
`publicar-azure.yml` ahora **llama primero a `ci.yml`**: si algo falla, no se despliega.

## 4. SonarQube

1. En tu servidor SonarQube: crea el proyecto con la clave `siger-backend` (la del archivo `sonar-project.properties`).
2. Genera un token (Mi cuenta > Seguridad).
3. En GitHub: *Settings > Secrets and variables > Actions* y crea `SONAR_TOKEN` y `SONAR_HOST_URL` (ej. `https://sonar.tudominio.com`).
4. (Recomendado) Crea un Quality Gate propio con **cobertura global >= 70 %** y asignalo al proyecto: el de fabrica solo exige cobertura sobre el codigo *nuevo*.
5. En *Settings > Branches* de GitHub protege `main` y marca el check **CI** como obligatorio.

Mientras no existan los secretos, el CI sigue corriendo las pruebas y solo muestra un aviso de que SonarQube se omitio.
Si en vez de un servidor propio usas SonarQube Cloud, `SONAR_HOST_URL` es `https://sonarcloud.io` y hay que agregar `sonar.organization=<tu-organizacion>` a `sonar-project.properties`.
