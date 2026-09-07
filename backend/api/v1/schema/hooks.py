TAG_MAP = {
    'auth': 'Авторизация',
    'profile': 'Профиль',
    'exercises': 'Задания',
    'progress': 'Прогресс',
}

def add_tags_by_path(result, generator, request, public):
    prefix = '/api/v1/'
    for path, methods in result['paths'].items():
        if path.startswith(prefix):
            segments = path[len(prefix):].split('/')
            first = segments[0]
            key = 'profile' if (first == 'auth' and len(segments) > 1 and segments[1] == 'users') else first
        else:
            key = 'other'

        tag = TAG_MAP.get(key, key)

        for operation in methods.values():
            if isinstance(operation, dict) and 'operationId' in operation:
                operation['tags'] = [tag]

    return result
