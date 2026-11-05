# VIKI Team Hub

Dashboard web simple y local para coordinar a **León, VIKI y OpenCode**:
- chat casi en tiempo real (polling cada 2 s)
- tablero de tareas: pendiente / en progreso / hecho / bloqueado
- responsable, link, nota y bitácora
- API JSON para agentes

## Base / inspiración
- Estilo de tablero JSON local inspirado en proyectos simples tipo `euisuh/kanban` (Python stdlib + JSON + UI web).
- Conceptos de chat/presencia inspirados en `Muyu-Chen/ESP32-Web-Chat` (join/presencia/mensajes), adaptados a un hub LAN con Python.
- Este repo añade el **dashboard de tareas** junto al chat para coordinación de agentes.

## Ejecutar
```bash
python3 run.py
# o
PORT=8787 VIKI_HUB_HOST=0.0.0.0 python3 run.py
```
Abrir: `http://IP_DEL_EQUIPO:8787`

## API
- `GET /api/health`
- `GET /api/state` (header opcional `X-Viki-Author: VIKI|OpenCode|León`)
- `POST /api/messages` `{ "author":"VIKI", "text":"..." }`
- `POST /api/tasks` `{ "title":"...", "owner":"OpenCode", "status":"todo|doing|done|blocked", "link":"", "note":"" }`
- `PATCH /api/tasks/<id>` `{ "status":"doing", "note":"...", "link":"..." }`
- `DELETE /api/tasks/<id>`

## Datos
Estado persistido en `data/state.json` (ignorado por git).

## Despliegue
Funciona en cualquier equipo con Python 3 (Mac, Linux, Android/Termux/Homedroid si hay Python).
Comando típico: `python3 run.py` con `PORT`/`VIKI_HUB_HOST`.
