# Landing Yiga5 (ultraligera)

Landing estática enfocada en conversión con CTA directo a WhatsApp.

Incluye ahora un microservicio opcional para recuperar conversaciones de clientes por WhatsApp (Twilio), ver historial y responder manualmente.

## Requisitos

- Docker
- Docker Compose (plugin `docker compose`)

## Ejecutar

```bash
docker compose up --build -d
```

Abre: http://localhost:10000

Landing: http://localhost:10050

CRM WhatsApp (bandeja): http://localhost:18000/inbox

## Detener

```bash
docker compose down
```

## Archivos clave

- `index.html`: estructura de la landing
- `styles.css`: estilos livianos sin frameworks
- `script.js`: scroll suave para anclas
- `Dockerfile`: imagen basada en `nginx:alpine`
- `docker-compose.yml`: servicio listo para correr
- `backend/app.py`: webhook Twilio + API de conversaciones + bandeja simple

## Twilio WhatsApp (recuperar conversación y responder)

1) Define variables de entorno antes de levantar contenedores:

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="tu_auth_token"
export TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886"
```

2) Levanta servicios:

```bash
docker compose up --build -d
```

3) En Twilio Console (WhatsApp Sender), configura webhook entrante:

- URL: `https://TU_DOMINIO/webhook/twilio/whatsapp`
- Método: `POST`

Si pruebas local, usa túnel (por ejemplo `ngrok`) y pega la URL pública apuntando al puerto `18000`.

4) Flujo:

- Cliente escribe por WhatsApp.
- Twilio envía evento a `/webhook/twilio/whatsapp`.
- Se guarda en SQLite (`backend/conversations.db`).
- Operador responde desde `http://localhost:18000/inbox` cuando sea necesario.
