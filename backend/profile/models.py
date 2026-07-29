from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from .constants import MAX_TEXT_CHOICE_LEN, STATUS_LEN, TYPE_LEN, QUESTION_TEXT
from exercises.models import Exercise


class Attempt(models.Model):
    """Модель попытки прохождения задания."""

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'В процессе'
        COMPLETED = 'completed', 'Завершено'
        ABANDONED = 'abandoned', 'Брошено'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    task = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    status = models.CharField(
        max_length=STATUS_LEN,
        choices=Status.choices,
        default=Status.IN_PROGRESS
    )
    score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Итоговый балл (0-100)'
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-started_at']
        unique_together = [['user', 'task', 'attempt_number']]

    def __str__(self):
        return (
            f'{self.user.username} - {self.task.title}'
            f'(попытка {self.attempt_number})'
        )

    def save(self, *args, **kwargs):
        """Функция автоматического проставления номера попытки."""
        if not self.pk and not self.attempt_number:
            last_attempt = Attempt.objects.filter(
                user=self.user,
                task=self.task
            ).order_by('-attempt_number').first()
            self.attempt_number = (
                last_attempt.attempt_number + 1
                if last_attempt
                else 1
            )
        super().save(*args, **kwargs)

    def can_complete(self):
        """Функция проверки возможности завершить попытку."""
        return self.status == self.Status.IN_PROGRESS

    def calculate_score(self):
        """Функция расчета процента правильных ответов."""
        answers = self.answers.all()
        if not answers:
            return 0

        total_points = 0
        earned_points = 0

        for answer in answers:
            question = answer.question
            total_points += question.points

            # Для разных типов вопросов своя логика проверки
            if question.type == Question.Type.CHOICE:
                if answer.is_correct:
                    earned_points += question.points
            elif question.type == Question.Type.TEXT_INPUT:
                if answer.is_correct:
                    earned_points += question.points
            elif question.type == Question.Type.SELECT_WORDS:
                if answer.is_correct:
                    earned_points += question.points
            elif question.type == Question.Type.MATCH:
                if answer.is_correct:
                    earned_points += question.points

        return (
            int((earned_points / total_points) * 100)
            if total_points > 0
            else 0
        )

    def complete(self):
        """Функция завершения попытки и рассчета результата."""
        if not self.can_complete():
            raise ValidationError('Нельзя завершить эту попытку')

        self.score = self.calculate_score()
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        return self.score


class Question(models.Model):
    """Модель вопроса внутри задания."""

    class Type(models.TextChoices):
        CHOICE = 'choice', 'Выбор ответа'
        SELECT_WORDS = 'select_words', 'Выделение слов'
        MATCH = 'match', 'Сопоставление'
        TEXT_INPUT = 'text_input', 'Ввод текста'

    task = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    type = models.CharField(
        max_length=TYPE_LEN,
        choices=Type.choices,
        default=Type.CHOICE,
        help_text='Тип вопроса'
    )
    text = models.TextField(
        help_text='Текст вопроса или инструкция'
    )
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)

    # Поле для хранения данных задания в JSON
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Дополнительные данные для задания'
    )

    def __str__(self):
        return f'{self.get_type_display()}: {self.text[:QUESTION_TEXT]}'


class Choice(models.Model):
    """Модель варианта ответа для вопросов с выбором."""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices'
    )
    text = models.CharField(max_length=MAX_TEXT_CHOICE_LEN)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.question.text[:30]} - {self.text[:30]}"


class Answer(models.Model):
    """Модель ответа пользователя на вопрос или выполнение задания."""
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    text_answer = models.TextField(
        'Текстовый ответ',
        blank=True,
        null=True,
        help_text='Для вопросов типа TEXT_INPUT'
    )
    selected_words = models.JSONField(
        'Выделенные слова',
        blank=True,
        null=True,
        help_text='Для вопросов типа SELECT_WORDS'
    )
    matches = models.JSONField(
        'Сопоставления',
        blank=True,
        null=True,
        help_text='Для вопросов типа MATCH: {"left_id": "right_id"}'
    )
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [['attempt', 'question']]

    def __str__(self):
        return (
            f'{self.attempt.user.username}'
            f' - {self.question.text[:QUESTION_TEXT]}'
        )

    def save(self, *args, **kwargs):
        """
        Функция автоматического определения правильности ответа
        в зависимости от типа вопроса.
        """
        question = self.question

        if question.type == Question.Type.CHOICE:
            # Проверка выбранного варианта
            if self.selected_choice:
                self.is_correct = self.selected_choice.is_correct
            else:
                self.is_correct = False

        elif question.type == Question.Type.TEXT_INPUT:
            # Проверка текстового ответа
            if self.text_answer:
                correct_text = question.data.get('correct_text', '')
                # Сравниваем без учета регистра и лишних пробелов
                user_answer = self.text_answer.lower().strip()
                correct_answer = correct_text.lower().strip()
                self.is_correct = user_answer == correct_answer
            else:
                self.is_correct = False

        elif question.type == Question.Type.SELECT_WORDS:
            # Проверка выделенных слов
            if self.selected_words:
                correct_words = question.data.get('correct_words', [])
                # Сравниваем списки (порядок не важен)
                self.is_correct = (
                    set(self.selected_words) == set(correct_words)
                )
            else:
                self.is_correct = False

        elif question.type == Question.Type.MATCH:
            # Проверка сопоставлений
            if self.matches:
                correct_matches = question.data.get('correct_matches', {})
                # Сравниваем словари сопоставлений
                self.is_correct = self.matches == correct_matches
            else:
                self.is_correct = False

        super().save(*args, **kwargs)
