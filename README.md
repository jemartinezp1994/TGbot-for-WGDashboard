🤖 WGDashboard Telegram Bot
Bot de Telegram para gestionar y monitorear remotamente servidores WireGuard a través de WGDashboard.

✨ Características
🔧 Gestión de Configuraciones WireGuard
📡 Listar todas las configuraciones disponibles

⚙️ Ver detalles específicos de cada configuración

🔄 Actualizar información en tiempo real

👥 Administración de Peers
👤 Listar todos los peers (conectados y desconectados)

📋 Ver información detallada de cada peer

🗑️ Eliminar peers existentes

➕ Agregar nuevos peers automáticamente

📥 Descargar configuraciones en formato .conf

🚫 Gestionar restricciones de acceso

⏰ Schedule Jobs (Trabajos Programados)
📊 Establecer límites de datos (en GB)

📅 Configurar fechas de expiración

🔄 Crear y eliminar jobs automáticamente

⚡ Acción automática: RESTRICT cuando se alcanza el límite

🖥 Monitoreo del Sistema
💻 Estado de CPU y uso de memoria

💾 Uso de discos y espacio disponible

📡 Estadísticas de interfaces de red

🔗 Monitoreo específico de interfaces WireGuard

📊 Estadísticas y Reportes
📈 Resumen general de todas las configuraciones

📊 Tasa de conexión de peers

⚡ Protocolos habilitados

📶 Estado del sistema en tiempo real

🚀 Requisitos Previos
Software Necesario
Python 3.8 o superior

WGDashboard v4.2.0 o superior

Acceso a la API de WGDashboard habilitado

Servidor con WireGuard configurado

Cuentas y Accesos
Token de Bot de Telegram (obtenido desde @BotFather)

API Key de WGDashboard

URL del servidor WGDashboard

📋 Instalación Paso a Paso
1. Clonar el repositorio
bash
git clone https://github.com/tu-usuario/wgdashboard-bot.git
cd wgdashboard-bot
2. Crear entorno virtual
bash
python3 -m venv venv
source venv/bin/activate
En Windows:

bash
venv\Scripts\activate
3. Instalar dependencias
bash
pip install -r requirements.txt
4. Configurar variables de entorno
Crear un archivo .env en la raíz del proyecto con el siguiente contenido:

env
TELEGRAM_BOT_TOKEN=tu_token_aqui
WG_API_BASE_URL=https://tu-servidor.com/api
WG_API_KEY=tu_api_key_aqui
WG_API_PREFIX=
API_TIMEOUT=10
LOG_FILE=wg_bot.log
LOG_LEVEL=INFO
MAX_PEERS_DISPLAY=10
5. Configurar usuarios autorizados
Editar el archivo config.py y agregar tu ID de Telegram:

python
ALLOWED_USERS = {
    762494594: "Tu Nombre"
}
Para obtener tu ID de Telegram:

Busca @userinfobot en Telegram

Envía el comando /start

Copia tu ID numérico

6. Configurar WGDashboard
Habilitar la API en WGDashboard

Generar una API Key

Verificar que la URL de la API sea accesible desde el bot

7. Probar la conexión
bash
python3 main.py
Salida esperada:

text
Configuración validada correctamente
Iniciando Bot WGDashboard
Bot WGDashboard inicializado
🎮 Uso del Bot
Comandos disponibles
/start - Inicia el bot

/help - Muestra la ayuda

/stats - Muestra las estadísticas del sistema

/configs - Lista las configuraciones WireGuard

/cancel - Cancela la operación actual

Flujo de trabajo
Enviar el comando /start

Seleccionar "Configuraciones"

Elegir una configuración WireGuard

Gestionar los peers:

Descargar configuraciones

Ver detalles

Agregar peer

Eliminar peer

Gestionar Schedule Jobs

Gestionar Restricciones

Agregar un nuevo peer
Seleccionar la configuración deseada

Elegir la opción "Agregar Peer"

Enviar el nombre del peer

El bot generará automáticamente las claves, la IP y el archivo .conf

Schedule Jobs
Seleccionar la configuración deseada

Elegir la opción "Schedule Jobs"

Elegir el peer

Establecer el límite de datos en GB

Establecer la fecha de expiración en formato dd/mm/aaaa

🛠 Gestión como Servicio (Linux)
Crear un servicio systemd
Crear el archivo /etc/systemd/system/wgdashboard-bot.service con el siguiente contenido:

ini
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
Habilitar y arrancar el servicio
bash
sudo systemctl daemon-reload
sudo systemctl enable wgdashboard-bot
sudo systemctl start wgdashboard-bot
Script de gestión (manage.sh)
bash
./manage.sh start    # Iniciar el bot
./manage.sh stop     # Detener el bot
./manage.sh status   # Ver estado del bot
./manage.sh logs     # Ver logs
./manage.sh logs-today  # Ver logs de hoy
./manage.sh update   # Actualizar el bot
📁 Estructura del Proyecto
text
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
🔧 Solución de Problemas
Error de conexión a la API
Verificar que WG_API_BASE_URL sea correcta

Confirmar que la API esté habilitada en WGDashboard

Validar que la API Key sea correcta

El bot no responde
Verificar que el token del bot sea correcto

Revisar los logs en wg_bot.log

Confirmar que tu ID de Telegram esté en la lista de usuarios autorizados

No se pueden agregar peers
Verificar que la configuración de WireGuard esté activa

Revisar que haya rango de IPs disponibles

Consultar los logs para más detalles

🔐 Seguridad
Agregar solo administradores confiables a la lista de usuarios autorizados

No compartir las API Keys ni tokens del bot

No subir archivos .env o con información sensible a repositorios públicos

Proteger los archivos de logs que pueden contener información sensible

🤝 Contribuciones
Las contribuciones son bienvenidas. Por favor:

Haz un fork del repositorio

Crea una rama para tu funcionalidad (git checkout -b feature/nueva-funcionalidad)

Haz commit de tus cambios (git commit -am 'Añade nueva funcionalidad')

Haz push a la rama (git push origin feature/nueva-funcionalidad)

Abre un Pull Request

📄 Licencia
Este proyecto está bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.

❓ Soporte
Revisa la documentación en este README

Consulta los logs del bot

Si encuentras un problema, abre un issue en GitHub