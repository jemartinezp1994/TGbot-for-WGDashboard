"""
Punto de entrada principal del bot WGDashboard
"""

import signal
import sys
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Importar configuraciones y módulos
import config
from setup_logging import logger
from handlers import (
    start_command, help_command, stats_command, configs_command,
    callback_handler, text_message_handler
)
from utils import is_allowed

# ================= FUNCIONES DE UTILIDAD ================= #
def validate_environment():
    """Valida que todas las variables necesarias estén configuradas"""
    errors = config.validate_config()
    
    if errors:
        logger.error("❌ Errores de configuración encontrados:")
        for error in errors:
            logger.error(f"   - {error}")
        return False
    
    logger.info("✅ Configuración validada correctamente")
    return True

async def post_init(application):
    """Tareas a ejecutar después de inicializar el bot"""
    logger.info("🤖 Bot WGDashboard inicializado")
    logger.info(f"👥 Usuarios autorizados: {len(config.ALLOWED_USERS)}")
    
    # Información sobre el bot
    bot = await application.bot.get_me()
    logger.info(f"🤖 Nombre del bot: {bot.first_name}")
    logger.info(f"🤖 Username: @{bot.username}")
    logger.info(f"🤖 ID: {bot.id}")

async def post_stop(application):
    """Tareas a ejecutar al detener el bot"""
    logger.info("🛑 Bot deteniéndose...")
    # Aquí puedes agregar cleanup si es necesario

# ================= HANDLERS ================= #
def setup_handlers(application):
    """Configura todos los handlers del bot"""
    
    # Comandos principales
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Comandos solo para administradores
    from utils import is_admin
    async def stats_command_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text(
                "❌ *Acceso restringido*\n\n"
                "Este comando solo está disponible para administradores.",
                parse_mode="Markdown"
            )
            return
        await stats_command(update, context)
    
    async def configs_command_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text(
                "❌ *Acceso restringido*\n\n"
                "Este comando solo está disponible para administradores.",
                parse_mode="Markdown"
            )
            return
        await configs_command(update, context)
    
    application.add_handler(CommandHandler("stats", stats_command_admin))
    application.add_handler(CommandHandler("configs", configs_command_admin))
    
    # Callbacks (botones inline)
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Handler para mensajes de texto (para agregar peers)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_message_handler
    ))
    
    logger.info("✅ Handlers configurados correctamente")

# ================= MANEJO DE SEÑALES ================= #
def signal_handler(signum, frame):
    """Maneja señales de sistema para shutdown graceful"""
    logger.info(f"📡 Señal {signum} recibida, deteniendo bot...")
    # Esto se manejará en el loop principal

# ================= MAIN ================= #
def main():
    """Función principal"""
    
    logger.info("🚀 Iniciando Bot WGDashboard...")
    
    # Validar configuración
    if not validate_environment():
        sys.exit(1)
    
    try:
        # Crear aplicación de Telegram
        application = ApplicationBuilder() \
            .token(config.TELEGRAM_BOT_TOKEN) \
            .post_init(post_init) \
            .post_shutdown(post_stop) \
            .build()
        
        # Configurar handlers
        setup_handlers(application)
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Iniciar el bot
        logger.info("🔄 Iniciando polling...")
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
            close_loop=False
        )
        
    except Exception as e:
        logger.error(f"❌ Error crítico al iniciar el bot: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("👋 Bot detenido correctamente")

if __name__ == "__main__":
    main()
