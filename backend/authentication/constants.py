PURPOSE_LENGTH: int = 20
"""Длина поля "Назначение" кода."""

CODE_LENGTH: int = 6
"""Длина одноразового кода."""

CODE_TTL_MINUTES: int = 10
"""Срок действия кода (в минутах)."""

MAX_VERIFY_ATTEMPTS: int = 5
"""Максимум неверных попыток ввода кода."""

CODE_COOLDOWN_SECONDS: int = 60
"""Кулдаун между отправками кода (в секундах)."""

MAX_CODES_PER_HOUR: int = 5
"""Максимум отправленных кодов за час."""
