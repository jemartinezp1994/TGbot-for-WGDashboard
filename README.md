# 🤖 WGDashboard Telegram Bot

Un bot de Telegram para gestionar y monitorear remotamente servidores WireGuard a través de WGDashboard.

✨ Características Principales

🔧 Gestión de Configuraciones WireGuard  
📡 Listar todas las configuraciones disponibles  
⚙️ Ver detalles específicos de cada configuración  
🔄 Actualizar información en tiempo real  

👥 Administración de Peers  
👤 Listar todos los peers (conectados/desconectados)  
📋 Ver información detallada de cada peer  
🗑 Eliminar peers existentes  
➕ Agregar nuevos peers automáticamente  
📥 Descargar configuraciones en formato .conf  
🚫 Gestionar restricciones de acceso  

⏰ Schedule Jobs (Trabajos Programados)  
📊 Establecer límites de datos (GB)  
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
Acceso a API de WGDashboard habilitado  
Servidor con WireGuard configurado  

Cuentas y Accesos  
Token de Bot de Telegram (obtenido desde @BotFather)  
API Key de WGDashboard  
URL del servidor WGDashboard  

📋 Instalación Paso a Paso

Clonar el repositorio  
git clone https://github.com/tu-usuario/wgdashboard-bot.git  
cd wgdashboard-bot  

Crear entorno virtual  
python3 -m venv venv  
source venv/bin/activate  
Windows: venv\Scripts\activate  

Instalar dependencias  
pip install -r requirements.txt  

Configurar variables de entorno  
Crear archivo .env en la raíz del proyecto con el siguiente contenido:

TELEGRAM_BOT_TOKEN=tu_token_aqui  
WG_API_BASE_URL=https://tu-servidor.com/api  
WG_API_KEY=tu_api_key_aqui  
WG_API_PREFIX=  
API_TIMEOUT=10  
LOG_FILE=wg_bot.log  
LOG_LEVEL=INFO  
MAX_PEERS_DISPLAY=10  

Configurar usuarios autorizados  
Editar el archivo config.py y agregar tu ID de Telegram:

ALLOWED_USERS = {  
    762494594: "Tu Nombre"  
}  

Para obtener tu ID de Telegram:  
Busca @userinfobot  
Envía /start  
Copia tu ID numérico  

Configurar WGDashboard  
Habilitar la API  
Generar una API Key  
Verificar que la URL sea accesible desde el bot  

Probar la conexión  
python3 main.py  

Salida esperada:  
Configuración validada correctamente  
Iniciando Bot WGDashboard  
Bot WGDashboard inicializado  

🎮 Uso del Bot

Comandos disponibles  
/start Inicia el bot  
/help Muestra ayuda  
/stats Estadísticas del sistema  
/configs Lista configuraciones  
/cancel Cancela operación  

Flujo de trabajo  
Enviar /start  
Seleccionar Configuraciones  
Elegir una configuración WireGuard  
Gestionar peers:  
Descargar configuraciones  
Ver detalles  
Agregar peer  
Eliminar peer  
Schedule Jobs  
Restricciones  

Agregar nuevo peer  
Seleccionar configuración  
Agregar Peer  
Enviar nombre del peer  
El bot genera automáticamente claves, IP y archivo .conf  

Schedule Jobs  
Seleccionar configuración  
Schedule Jobs  
Elegir peer  
Límite de datos en GB  
Fecha de expiración en formato dd/mm/aaaa  

🛠 Gestión como Servicio (Linux)

Crear servicio systemd en /etc/systemd/system/wgdashboard-bot.service con el siguiente contenido:

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

Habilitar servicio  
systemctl daemon-reload  
systemctl enable wgdashboard-bot  
systemctl start wgdashboard-bot  

Script de gestión manage.sh  
./manage.sh start  
./manage.sh stop  
./manage.sh status  
./manage.sh logs  
./manage.sh logs-today  
./manage.sh update  

📁 Estructura del Proyecto

wgdashboard-bot/  
main.py  
handlers.py  
keyboards.py  
wg_api.py  
utils.py  
config.py  
setup_logging.py  
manage.sh  
requirements.txt  
.env  
README.md  

🔧 Solución de Problemas

Error de conexión a la API  
Verificar WG_API_BASE_URL  
Confirmar API habilitada  
Validar API Key  

Bot no responde  
Verificar token  
Revisar logs  
Confirmar ID autorizado  

No se pueden agregar peers  
Verificar configuración WireGuard  
Revisar rango de IPs  
Consultar logs  

🔐 Seguridad

Usar solo administradores confiables  
No compartir API Keys  
No subir tokens a repositorios públicos  
Proteger archivos de logs  

🤝 Contribuir

Fork del repositorio  
Crear rama  
Commit de cambios  
Push  
Pull Request  

📄 Licencia

MIT License  

❓ Soporte

Revisar documentación  
Ver logs  
Abrir un issue en GitHub
