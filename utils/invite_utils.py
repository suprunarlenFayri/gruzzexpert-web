import secrets
import string

from models import Workspace

DEFAULT_WORKSPACE_ID = 1
INVITE_KEY_LENGTH = 23


def generate_invite_key(length=INVITE_KEY_LENGTH):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        key = ''.join(secrets.choice(alphabet) for _ in range(length))
        if not Workspace.query.filter_by(invite_key=key).first():
            return key


def workspace_has_director(workspace_id):
    from models import User

    return (
        User.query.filter_by(workspace_id=workspace_id, role='director').first()
        is not None
    )
