# Landing Yiga5 (ultraligera)

Landing estática enfocada en conversión con CTA directo a WhatsApp.

## Requisitos

- Docker
- Docker Compose (plugin `docker compose`)

## Ejecutar

```bash
docker compose up --build -d
```

Abre: http://localhost:10000

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
