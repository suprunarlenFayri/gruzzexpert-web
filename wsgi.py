"""Точка входа для Gunicorn / облачного деплоя."""
import os

from app import create_app

application = create_app()

if __name__ == '__main__':
    from socketio_instance import socketio

    port = int(os.getenv('PORT', '5001'))
    socketio.run(application, host='0.0.0.0', port=port)
