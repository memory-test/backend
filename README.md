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
Поднимает все сервисы, необходимые локально. В их число не входит веб-сервер nginx и dozzle

### Применяем миграции и создаем суперпользователя:
```bash
docker  compose  exec  -it  web  python  backend/manage.py  migrate
docker  compose  exec  -it  web  python  backend/manage.py  createsuperuser
```
> Примечание: команда migrate применяет в том числе миграции django_celery_beat (таблицы для периодических задач Celery).

### Доступ к приложению
* Откройте http://localhost:8000/ в браузере

## Установка новых зависимостей
###  Устанавливаем
```bash
docker  compose  exec  -it  web  pip install <new_lib_name>
```
###  Фиксируем новое окружение в файле для pip
```bash
docker  compose  exec  -it  web pip freeze > ./requirements.txt
```
###  Пересобираем образ приложения с новым окружением и перестартуем проект
```bash
docker compose build web
docker compose up -d
```

## ✅ Проверка кода перед PullRequest

Форматируем:
```bash
docker  compose  run  --rm  -it  web  ruff  format
```

Исправляем более существенные проблемы (неиспользуемые импорты и т.п.):
```bash
docker compose exec web ruff check . --fix
```

Запуск всех проверок и тестов так же, как при production-деплое.
Должен завершится `[ci finished]`:

```bash
docker  compose  run  --rm  -it  web  bash  ./docker/django/ci.sh
```


## 🔄 Команды обслуживания и решение проблем

Очистка проекта (удаляет volumes, включая базу данных):
```bash
docker  compose  down  -v
```

Пересборка контейнера (если изменились зависимости или возникли проблемы):
```bash
docker  compose  build  web
docker  compose  up  -d
```


## 🗂️ Тестовые данные

### Запуск

```bash
# Идемпотентный прогон (дублей не создаёт)
docker compose exec -it web python backend/manage.py seed_demo

# Сбросить и пересоздать с нуля
docker compose exec -it web python backend/manage.py seed_demo --flush
```

### Учётные записи

| Роль | Email | Пароль |
|---|---|---|
| HR-admin | `hr1@demo.local` | `demo12345` |
| HR-admin | `hr2@demo.local` | `demo12345` |
| employee | `emp1@demo.local` | `demo12345` |
| employee | `emp2@demo.local` | `demo12345` |
| employee | `emp3@demo.local` | `demo12345` |
| employee | `emp4@demo.local` | `demo12345` |
| employee | `emp5@demo.local` | `demo12345` |

### Что создаётся

| Объект | Кол-во |
|---|---|
| HR-администраторы | 2 |
| Пользователи-сотрудники | 5 |
| Направления (`type=direction`) | 3 |
| Отделы (`type=department`) | 9 |
| Теги | 10 |
| Карточки сотрудников | 18 (5 с привязанным user, 13 без) |

### Оргструктура

```
Технологии и разработка
  - Разработка ПО
  - DevOps и инфраструктура
  - QA и тестирование

Маркетинг и продажи
  - Цифровой маркетинг
  - Отдел продаж
  - Аналитика

Операционная деятельность
  - HR и кадры
  - Финансы
  - Административный отдел
```

### Использование фабрик в тестах

```python
from tests.factories.factories import (
    UserFactory, HRAdminFactory,
    DirectionFactory, DepartmentFactory,
    EmployeeFactory, TagFactory,
)

direction  = DirectionFactory()
department = DepartmentFactory(type="department", parent=direction)
employee   = EmployeeFactory(department=department)
hr_user    = HRAdminFactory()
tag        = TagFactory(name="Python")
```

> Данные воспроизводимы: `Faker('ru_RU')` с фиксированным `seed=42`.