# 🤖 WGDashboard Telegram Bot

Bot de Telegram para administrar y consultar información de WireGuard mediante la API de WGDashboard. Permite a operadores autorizados gestionar peers, ver el estado del servidor y ejecutar acciones administrativas directamente desde Telegram.

## ✨ Características

✅ Autenticación de operadores autorizados

✅ Consulta del estado del servidor WireGuard

✅ Listado y gestión de peers

✅ Comunicación segura con la API de WGDashboard

✅ Menús interactivos con botones inline

✅ Arquitectura modular

✅ Sistema de logging centralizado

✅ Script de gestión para iniciar y detener el bot  

## 📁 Estructura del proyecto

bot/
├── main.py                        # Punto de entrada del bot  
├── config.py                      # Configuración y variables de entorno  
├── handlers.py                    # Handlers de comandos y callbacks  
├── keyboards.py                   # Teclados inline de Telegram  
├── operators.py                   # Control de operadores autorizados  
├── utils.py                       # Funciones utilitarias  
├── wg_api.py                      # Cliente de la API WGDashboard  
├── setup_logging.py               # Configuración de logs  
├── manage.sh                      # Script para gestionar el bot  
└── requirements.txt               # Dependencias del proyecto  

## 🛠️ Requisitos

- Python 3.9 o superior  
- WireGuard instalado y configurado  
- WGDashboard funcionando  
- Bot de Telegram creado con @BotFather  
- Servidor Linux (recomendado Ubuntu 20.04 o superior)  

## 📦 Instalación

### 1. Clonar el repositorio
```
git clone https://github.com/jemartinezp1994/TGbot-for-WGDashboard.git  
cd wgdashboard-telegram-bot  
```

2. Instalar dependencias
```
pip install -r requirements.txt
```
## ⚙️ Configuración

El bot utiliza variables de entorno. Crear un archivo .env en la raíz del proyecto:

``` 
TELEGRAM_BOT_TOKEN=tu_token_aqui
WG_API_BASE_URL=https://tu-url/api
WG_API_KEY=tu_api_key
WG_API_PREFIX=wg
API_TIMEOUT=10
LOG_FILE=wg_bot.log
LOG_LEVEL=INFO
MAX_PEERS_DISPLAY=10
```

### 🚀 Ejecución del bot

#### Ejecución directa
```
python main.py
```

##  📋 Comandos del bot

Comando	Descripción

/start	Inicia el bot

/menu	Muestra el menú principal

/status	Muestra el estado de WireGuard

/peers	Lista los peers

/help	Muestra ayuda

###  ⚠️ Algunos comandos pueden requerir permisos de operador.

##   🔐 Operadores y permisos

El acceso al bot está restringido a operadores autorizados. La lógica de autorización se encuentra en el archivo operators.py, donde se definen los IDs de Telegram permitidos y los niveles de acceso.

Para agregar operadores, edita el archivo config.py y agrega los IDs correspondientes.

python
# Administradores (acceso completo)
ADMINS = [123456789, 987654321]

# Operadores (acceso limitado)
OPERATORS = [112233445, 556677889]


##  📝 Logs

La configuración de logs se encuentra en setup_logging.py e incluye logs informativos, errores y eventos del sistema del bot. Los logs se guardan en el archivo especificado en la variable LOG_FILE.

## 🏗️ Arquitectura
Basado en python-telegram-bot v20+

Uso de programación asíncrona con asyncio

Separación clara de responsabilidades

Preparado para ampliaciones futuras

🌍 Despliegue recomendado
VPS con Ubuntu 20.04 o superior

Ejecutar como servicio systemd o dentro de tmux

WGDashboard detrás de nginx

Firewall activo y acceso restringido

### Configurar como servicio systemd
bash
``` bash sudo nano /etc/systemd/system/wg-bot.service
```

Agrega el siguiente contenido:

``` bash [Unit]
Description=WGDashboard Telegram Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/al/bot
ExecStart=/usr/bin/python3 /ruta/al/bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
## 📄 Licencia
Este proyecto se distribuye bajo la licencia MIT. Puedes usarlo, modificarlo y redistribuirlo libremente.

Ver archivo LICENSE para más detalles.

## 👨‍💻 Autor
Jorge Elián Martinez Perdomo
Bot de Telegram para administración profesional de WireGuard usando WGDashboard

### GitHub: @jemartinezp1994

## Contribuciones
Las contribuciones son bienvenidas. Por favor:

Fork el repositorio

Crea una rama para tu feature (git checkout -b feature/AmazingFeature)

Commit tus cambios (git commit -m 'Add AmazingFeature')

Push a la rama (git push origin feature/AmazingFeature)

Abre un Pull Request
