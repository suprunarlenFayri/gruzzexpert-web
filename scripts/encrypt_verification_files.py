"""Однократное шифрование legacy-файлов анкет в uploads/verification/."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from models import VerificationRequest, db
from utils.secure_media import migrate_plain_verification_files


def main():
    app = create_app()
    with app.app_context():
        count = migrate_plain_verification_files(app, VerificationRequest.query.all())
        print(f'Migrated {count} verification file field(s).')


if __name__ == '__main__':
    main()
