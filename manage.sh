#!/bin/bash

SERVICE_NAME="wgdashboard-bot.service"

case "$1" in
    start)
        sudo systemctl start $SERVICE_NAME
        ;;
    stop)
        sudo systemctl stop $SERVICE_NAME
        ;;
    restart)
        sudo systemctl restart $SERVICE_NAME
        ;;
    status)
        sudo systemctl status $SERVICE_NAME
        ;;
    logs)
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    logs-today)
        sudo journalctl -u $SERVICE_NAME --since today
        ;;
    update)
        echo "Deteniendo el bot..."
        sudo systemctl stop $SERVICE_NAME
        echo "Actualizando desde git..."
        git pull
        echo "Instalando dependencias..."
        pip3 install -r requirements.txt
        echo "Iniciando el bot..."
        sudo systemctl start $SERVICE_NAME
        echo "Verificando estado..."
        sudo systemctl status $SERVICE_NAME
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs|logs-today|update}"
        exit 1
        ;;
esac
