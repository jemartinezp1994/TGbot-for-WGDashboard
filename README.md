# 🤖 WGDashboard Telegram Bot

Bot de Telegram para **gestionar y monitorear remotamente servidores WireGuard** mediante **WGDashboard**, permitiendo una administración centralizada, segura y automatizada directamente desde Telegram.

---

## ✨ Características

**Gestión de WireGuard**

* Listar todas las configuraciones disponibles
* Ver detalles de cada configuración
* Actualización de información en tiempo real

**Administración de Peers**

* Listar peers conectados y desconectados
* Ver información detallada
* Agregar peers automáticamente
* Eliminar peers existentes
* Descargar configuraciones `.conf`
* Gestionar restricciones de acceso

**Schedule Jobs**

* Límites de datos (GB)
* Fechas de expiración
* Creación y eliminación automática de jobs
* Acción automática **RESTRICT** al alcanzar el límite

**Monitoreo del Sistema**

* CPU y memoria
* Disco y espacio disponible
* Estadísticas de red
* Interfaces WireGuard

**Estadísticas**

* Resumen general
* Tasa de conexión de peers
* Protocolos habilitados
* Estado del sistema en tiempo real

---

## 🚀 Requisitos

* Python 3.8+
* WGDashboard v4.2.0+
* WireGuard configurado
* API de WGDashboard habilitada
* Token de Bot de Telegram (BotFather)
* API Key de WGDashboard
* URL del servidor WGDashboard

---

## 📦 Instalación

```bash
git clone https://github.com/tu-usuario/wgdashboard-bot.git
cd wgdashboard-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

En Windows:

```bash
venv\Scripts\activate
```

---

## ⚙️ Configuración

Archivo `.env`:

```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
WG_API_BASE_URL=https://tu-servidor.com/api
WG_API_KEY=tu_api_key_aqui
WG_API_PREFIX=
API_TIMEOUT=10
LOG_FILE=wg_bot.log
LOG_LEVEL=INFO
MAX_PEERS_DISPLAY=10
```

`config.py`:

```python
ALLOWED_USERS = {
    762494594: "Tu Nombre"
}
```

Obtener ID de Telegram:

* @userinfobot → /start → copiar ID

---

## ▶️ Ejecución

```bash
python3 main.py
```

---

## 🎮 Comandos

* /start
* /help
* /stats
* /configs
* /cancel

---

## ➕ Agregar Peer

Seleccionar configuración → Agregar Peer → Enviar nombre
El bot genera automáticamente: claves, IP y archivo `.conf`

---

## ⏰ Schedule Jobs

Configuración → Schedule Jobs → Peer → Límite GB → Fecha (dd/mm/aaaa)

---

## 🛠 Servicio systemd (Linux)

```ini
[Unit]
Description=WGDashboard Telegram Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/al/wgdashboard-bot
ExecStart=/ruta/al/venv/bin/python3 /ruta/al/wgdashboard-bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wgdashboard-bot
sudo systemctl start wgdashboard-bot
```

---

## 📜 manage.sh

```bash
./manage.sh start
./manage.sh stop
./manage.sh status
./manage.sh logs
./manage.sh logs-today
./manage.sh update
```

---

## 📁 Estructura

```text
wgdashboard-bot/
├── main.py
├── handlers.py
├── keyboards.py
├── wg_api.py
├── utils.py
├── config.py
├── setup_logging.py
├── manage.sh
├── requirements.txt
├── .env
└── README.md
```

---

## 🔧 Problemas Comunes

**API**

* Verificar URL
* API habilitada
* API Key correcta

**Bot**

* Token válido
* ID autorizado
* Revisar logs

**Peers**

* Configuración activa
* IPs disponibles
* Revisar logs

---

## 🔐 Seguridad

* Solo admins confiables
* No compartir tokens
* No subir `.env`
* Proteger logs

---

## 🤝 Contribuciones

Fork → Rama → Commit → Push → Pull Request

---

## 📄 Licencia

MIT – ver archivo LICENSE

---

## ❓ Soporte

Revisa este README, los logs o abre un Issue en GitHub
