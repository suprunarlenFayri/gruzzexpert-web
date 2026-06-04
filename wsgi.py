"""Точка входа для Gunicorn / облачного деплоя."""
import os

from app import create_app

application = create_app()

with application.app_context():
    from utils.app_bootstrap import run_startup_bootstrap

    print('====== FORCE RUNNING BOOTSTRAP FROM ENTRYPOINT ======', flush=True)
    try:
        run_startup_bootstrap()
        print('====== BOOTSTRAP EXECUTED SUCCESSFULLY ======', flush=True)
    except Exception as e:
        print(f'====== BOOTSTRAP FAILED WITH ERROR: {e} ======', flush=True)

if __name__ == '__main__':
    from socketio_instance import socketio

    port = int(os.getenv('PORT', '5001'))
    socketio.run(application, host='0.0.0.0', port=port)
