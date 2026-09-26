# Тесты (pytest_tests/)

Тесты написаны на `pytest` + `pytest-django`, без `Client`/`TestCase` из
стандартного Django — только фикстуры и обычные функции.

## Структура

```
pytest_tests/
├── conftest.py                  # общие фикстуры, если понадобятся всему проекту
├── auth/                        # аутентификация и профиль
│   ├── conftest.py              # фикстуры домена auth
│   ├── test_registration.py     # регистрация, повторная отправка кода активации
│   ├── test_code_verification.py# подтверждение кода (регистрация/вход), сроки, повтор
│   ├── test_password_login.py   # вход по паролю, refresh JWT
│   ├── test_password_reset.py   # сброс пароля по коду
│   ├── test_rate_limits.py      # кулдаун на запрос кода
│   ├── test_profile.py          # /auth/users/me/: возраст, прогресс, read-only поля
│   └── test_set_email.py        # смена email
└── exercises/                   # прохождение заданий (pass) по типам
    ├── conftest.py              # фикстуры домена exercises
    ├── choice/
    │   ├── test_single_answer.py    # выбор одного правильного варианта
    │   └── test_multiple_answer.py  # выбор нескольких правильных вариантов
    ├── input/
    │   ├── test_single_answer.py    # check_method=single_answer
    │   ├── test_list_answer.py      # check_method=list_answer
    │   └── test_free_answer.py      # check_method=free_answer
    └── test_matching.py         # сопоставление пар (matching)
```

## Где искать фикстуры

Общее правило: фикстура лежит в `conftest.py` того домена, тестам
которого она нужна. Тестовый файл никогда не объявляет свою
локальную фикстуру, если она нужна больше чем одному тесту в файле —
такая фикстура сразу уходит в `conftest.py` домена.

**`pytest_tests/exercises/conftest.py`**
- `user` — тестовый пользователь.
- `api_client` — авторизованный `APIClient` (уже с этим пользователем).
- `make_exercise(type_, title)` — создаёт активное задание нужного типа.
- `pass_exercise(exercise_id, **payload)` — отправляет `POST .../pass/`,
  сама подставляет `started_at`/`finished_at`/`duration_seconds`, вы
  добавляете только специфичные для типа поля (`answers_ids`,
  `answers`, `pairs`).
- `two_correct_exercise` — готовое задание `choice` с двумя верными
  и одним неверным вариантом.
- `four_words_exercise` — готовое задание `input` (`list_answer`) на
  четыре слова.
- `proverb_exercise` — готовое задание `input` (`free_answer`) с
  эталоном-рубрикой.
- `two_pairs_exercise` — готовое задание `matching` с двумя парами.

**`pytest_tests/auth/conftest.py`**
- `api_client` — неавторизованный `APIClient`.
- `post(path, data)` — POST-запрос с префиксом `/api/v1`.
- `register(...)`, `register_and_code(...)` — регистрация пользователя,
  вторая версия сразу достаёт код из письма.
- `active_user(...)` — создаёт уже активного пользователя, минуя флоу
  регистрации (для тестов, которым сама регистрация не важна).
- `auth(email, password)` — логинит и прописывает access-токен в
  `api_client`.
- `last_code()` — достаёт код подтверждения из последнего письма в
  тестовом outbox.
- `make_offline_exercise(...)`, `make_session(...)` — для тестов
  прогресса в профиле (`test_profile.py`).
- автоматические фикстуры (`locmem_email`, `clear_outbox`) — включают
  почтовый бэкенд `locmem` и чистят outbox перед каждым тестом,
  применять руками не нужно.

## Как запускать

```bash
uv run pytest                          # все тесты
uv run pytest pytest_tests/auth        # только авторизация
uv run pytest pytest_tests/exercises   # только задания
uv run pytest -k free_answer           # по подстроке в имени теста
```


## Соглашения при добавлении новых тестов

- Один домен (auth/exercises/новый раздел) — одна папка со своим
  `conftest.py`. Не тащите фикстуры одного домена в другой; если
  фикстура нужна обоим — поднимайте её в корневой
  `pytest_tests/conftest.py`.
- Имя теста описывает сценарий и ожидаемый результат:
  `test_<что_делаем>_<что_ожидаем>` (например,
  `test_partial_selection_fails`, `test_all_pairs_correct_succeeds`).
- Минимальный набор на новый сценарий: один «счастливый путь» +
  один-два негативных случая (неверный ответ, чужой id, невалидный
  формат). Не нужно покрывать то, что и так гарантирует DRF
  (`allow_empty=False` и подобное) — это не логика проекта.
- Новый тип задания получает отдельный файл `test_<тип>.py` (или
  подпапку, если у типа несколько разных сценариев проверки, как у
  `choice` и `input`), с фикстурой готового задания в
  `exercises/conftest.py`, если она пригодится больше чем одному
  тесту.
- Не создавайте `pytest_tests/base.py` и не наследуйтесь от
  самодельных базовых классов — весь проект на pytest-фикстурах, без
  классов `TestCase`.
