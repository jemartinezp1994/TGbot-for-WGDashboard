# 🤖 WGDashboard Telegram Bot

Bot de Telegram para administrar y consultar información de WireGuard mediante la API de WGDashboard. Permite a operadores autorizados gestionar peers, ver el estado del servidor y ejecutar acciones administrativas directamente desde Telegram.

## Características

Autenticación de operadores autorizados  
Consulta del estado del servidor WireGuard  
Listado y gestión de peers  
Comunicación segura con la API de WGDashboard  
Menús interactivos con botones inline  
Arquitectura modular  
Sistema de logging centralizado  
Script de gestión para iniciar y detener el bot  

## Estructura del proyecto

bot/
├── main.py              Punto de entrada del bot  
├── config.py            Configuración y variables de entorno  
├── handlers.py          Handlers de comandos y callbacks  
├── keyboards.py         Teclados inline de Telegram  
├── operators.py         Control de operadores autorizados  
├── utils.py             Funciones utilitarias  
├── wg_api.py            Cliente de la API WGDashboard  
├── setup_logging.py     Configuración de logs  
├── manage.sh            Script para gestionar el bot  
├── requirements.txt     Dependencias del proyecto  

## Requisitos

Python 3.9 o superior  
WireGuard instalado y configurado  
WGDashboard funcionando  
Bot de Telegram creado con @BotFather  
Servidor Linux recomendado Ubuntu 20.04 o superior  

## Instalación

Clonar el repositorio

git clone https://github.com/tu-usuario/wgdashboard-telegram-bot.git  
cd wgdashboard-telegram-bot  

Crear entorno virtual opcional

python3 -m venv venv  
source venv/bin/activate  

Instalar dependencias

pip install -r requirements.txt  

## Configuración

El bot utiliza variables de entorno. Crear un archivo .env en la raíz del proyecto

TELEGRAM_BOT_TOKEN=TU_TOKEN_DE_TELEGRAM  
WG_API_BASE_URL=http://localhost:10086/api  
WG_API_USERNAME=admin  
WG_API_PASSWORD=admin  

Nunca subas el archivo .env a GitHub

## Ejecución del bot

Ejecución directa

python main.py  

Usando el script de gestión

chmod +x manage.sh  
./manage.sh start  

Para detener el bot

./manage.sh stop  

## Comandos del bot

/start Inicia el bot  
/menu Muestra el menú principal  
/status Muestra el estado de WireGuard  
/peers Lista los peers  
/help Muestra ayuda  

Algunos comandos pueden requerir permisos de operador

## Operadores y permisos

El acceso al bot está restringido a operadores autorizados. La lógica de autorización se encuentra en el archivo operators.py donde se definen los IDs de Telegram permitidos y los niveles de acceso.

## Logs

La configuración de logs se encuentra en setup_logging.py e incluye logs informativos, errores y eventos del sistema del bot.

## Arquitectura

Basado en python-telegram-bot v20+  
Uso de programación asíncrona con asyncio  
Separación clara de responsabilidades  
Preparado para ampliaciones futuras  

## Despliegue recomendado

VPS con Ubuntu 20.04 o superior  
Ejecutar como servicio systemd o dentro de tmux  
WGDashboard detrás de nginx  
Firewall activo y acceso restringido  

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Puedes usarlo, modificarlo y redistribuirlo libremente.

## Autor

Jorge Elián Martinez Perdomo  
Bot de Telegram para administración profesional de WireGuard usando WGDashboard
