# VIKI Ops Panel (Homedroid)

Panel simple para coordinar León, VIKI y OpenCode en red local.

## Qué hace
- Chat en tiempo casi real (polling).
- Tablero de tareas: pendiente / en progreso / hecho / bloqueado.
- Links por tarea.
- Bitácora de cambios.

## Estructura
- `server.py`: servidor Python stdlib + API JSON + UI embebida.
- `data.json`: estado persistido (se crea al arrancar).
- `run.sh`: arranque local.

## API
- `GET /api/state` — estado completo
- `POST /api/messages` `{ "author":"VIKI", "text":"..." }`
- `POST /api/tasks` `{ "title":"...", "owner":"OpenCode", "status":"todo", "link":"", "note":"" }`
- `PATCH /api/tasks/<id>` `{ "status":"doing", "note":"...", "link":"..." }`

## Uso local (Mac)
```bash
cd ~/Videos/_comms/viki-ops-panel
python3 server.py --host 0.0.0.0 --port 8787
```
Abrir: `http://IP:8787`

## Despliegue en Homedroid
Repo/archivos: copiar esta carpeta como proyecto Python. Homedroid detecta Node/Python/static; para Python simple usar comando de arranque:
```bash
python3 server.py --host 0.0.0.0 --port $PORT
```
