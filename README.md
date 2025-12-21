# ?? WGDashboard Telegram Bot

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://telegram.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bot de Telegram para administrar y consultar informaci車n de WireGuard mediante la API de WGDashboard. Permite a operadores autorizados gestionar peers, ver el estado del servidor y ejecutar acciones administrativas directamente desde Telegram.

---

## ? Caracter赤sticas

- **?? Autenticaci車n de operadores autorizados** - Acceso restringido y seguro.
- **?? Consulta del estado del servidor** - Monitoriza el estado de WireGuard al instante.
- **?? Gesti車n completa de peers** - Lista, visualiza y administra los peers de WireGuard.
- **??? Comunicaci車n segura** - Interacci車n protegida con la API de WGDashboard.
- **??? Interfaz intuitiva** - Men迆s interactivos con botones inline para una navegaci車n sencilla.
- **??? Arquitectura modular** - C車digo organizado y preparado para ampliaciones.
- **?? Sistema de logging centralizado** - Registros detallados para depuraci車n y seguimiento.
- **?? Script de gesti車n** - Facilita el inicio y la detenci車n del servicio.

---

## ?? Requisitos Previos

- **Python 3.9** o superior.
- **WireGuard** instalado y configurado.
- **WGDashboard** funcionando y accesible.
- Un **Bot de Telegram** creado con [@BotFather](https://t.me/botfather).
- Servidor Linux (recomendado: **Ubuntu 20.04** o superior).

---

## ?? Instalaci車n R芍pida

**1. Clona el repositorio:** `git clone https://github.com/jemartinezp1994/TGbot-for-WGDashboard.git` y luego `cd wgdashboard-telegram-bot`

**2. Instala las dependencias:** `pip install -r requirements.txt`

---

## ?? Configuraci車n

El bot se configura mediante un archivo `.env`. Crea uno en la ra赤z del proyecto con el siguiente contenido:

`TELEGRAM_BOT_TOKEN=TU_TOKEN_AQUI`  
`WG_API_BASE_URL=https://tu_url_del_dashboard/api`  
`WG_API_KEY=TU_API_KEY`  
`WG_API_PREFIX=TU_PREFIJO`  
`API_TIMEOUT=10`  
`LOG_FILE=wg_bot.log`  
`LOG_LEVEL=INFO`  
`MAX_PEERS_DISPLAY=10`

---

## ?? Ejecuci車n

**M谷todo 1: Ejecuci車n directa con Python** - `python main.py`

**M谷todo 2: Usando el script de gesti車n**  
Primero, da permisos de ejecuci車n al script: `chmod +x manage.sh`  
Para iniciar el bot: `./manage.sh start`  
Para detenerlo: `./manage.sh stop`

---

## ?? Comandos Disponibles

| Comando | Descripci車n |
| :--- | :--- |
| `/start` | Inicia la interacci車n con el bot. |
| `/menu` | Muestra el men迆 principal interactivo. |
| `/status` | Consulta el estado actual del servidor WireGuard. |
| `/peers` | Lista los peers configurados. |
| `/help` | Muestra la gu赤a de ayuda y comandos. |

> **Nota:** Algunos comandos requieren permisos de operador.

---

## ?? Gesti車n de Operadores

El acceso administrativo est芍 limitado a operadores autorizados. La gesti車n de permisos y la lista de IDs de Telegram permitidos se configuran en el m車dulo `bot/operators.py`.

---

## ?? Logs

El sistema de logging se configura en `bot/setup_logging.py`. Los registros se escriben por defecto en `wg_bot.log` e incluyen informaci車n, errores y eventos del sistema para facilitar el monitoreo.

---

## ?? Arquitectura

- **Framework:** Basado en `python-telegram-bot` (v20.0+).
- **Paradigma:** Programaci車n as赤ncrona con `asyncio`.
- **Dise?o:** Arquitectura modular con separaci車n clara de responsabilidades.
- **Extensibilidad:** Estructura preparada para a?adir nuevas funcionalidades.

---

## ?? Despliegue Recomendado

Para un entorno de producci車n estable:
- **VPS** con **Ubuntu 20.04 LTS** o superior.
- Ejecutar el bot como un **servicio systemd** para mayor robustez.
- Ubicar **WGDashboard** detr芍s de un proxy inverso como **nginx**.
- Asegurar el servidor con un **firewall activo** y pol赤ticas de acceso restrictivas.

---

## ?? Licencia

Este proyecto est芍 bajo la **Licencia MIT**. Consulta el archivo `LICENSE` para m芍s detalles.

---

## ????? Autor

**Jorge Eli芍n Martinez Perdomo** - Bot de Telegram para administraci車n profesional de WireGuard usando WGDashboard