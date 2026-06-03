"""URL-хелперы для медиа и аватарок (чат, сокеты)."""


def avatar_path_for_user(user):
    if not user:
        return None
    path = getattr(user, 'avatar', None)
    if not path:
        return None
    path = str(path).replace('\\', '/').strip()
    for prefix in ('/static/uploads/', 'static/uploads/', '/uploads/', 'uploads/'):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    if '/' not in path:
        path = f'avatars/{path}'
    return path


def avatar_url_for(user, url_for_uploaded_file):
    path = avatar_path_for_user(user)
    if not path:
        return None
    return url_for_uploaded_file(path)
