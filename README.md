# backend

# Проект "Тренажер памяти"
Backend на Django DRF для веб-сайта.

## 🛠️ Старт локальной разработки в Docker

### Создаем файл с переменными окружения из шаблона:
```bash
cp  env.template  .env
```

### Запуск сервисов:
*Если локальных `docker images` нет — они будут загружены из DockerHub или собраны автоматически.*
```bash
docker  compose  up  -d
```
Поднимает все сервисы, необходимые локально (В их число не входит веб-сервер nginx и dozzle, которые описаны в отдельном серверном конфиге)

### Применяем миграции и создаем суперпользователя:
```bash
docker  compose  exec  -it backend  python  backend/manage.py  migrate
docker  compose  exec  -it backend  python  backend/manage.py  createsuperuser
```

### Доступ к приложению
* Откройте http://localhost:8000/ в браузере

## Установка новых зависимостей
###  Устанавливаем
```bash
docker  compose  exec  -it backend  uv add <new_lib_name>
```
###  Новый код не заработает в старом окружении, поэтому после добавления библиотек обязательно пересобираем образ и редеплоим проект
```bash
docker compose build backend
docker compose up -d
```

## ✅ Проверка кода перед PullRequest (TODO: не реализовано, но надо бы )

Форматируем:
```bash
docker  compose  run  --rm  -it backend  ruff  format
```

Исправляем более существенные проблемы (неиспользуемые импорты и т.п.):
```bash
docker compose exec backend ruff check . --fix
```

Запуск  проверок и тестов так же, как при production-деплое.

```bash
docker  compose  run  --rm  -it backend  python manage.py check --deploy
```


## 🔄 Команды обслуживания и решение проблем

Очистка проекта (удаляет volumes, включая базу данных):
```bash
docker  compose  down  -v
```

Пересборка контейнера (если изменились зависимости или возникли проблемы):
```bash
docker  compose  build  backend
docker  compose  up  -d
```
