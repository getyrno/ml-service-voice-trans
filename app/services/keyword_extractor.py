"""
NLP-модуль для автоматической экстракции ключевых слов из текста.
Использует TF-IDF подход для извлечения ключевых терминов.
"""
import re
from collections import Counter
from typing import List, Tuple, Optional
import math


# Стоп-слова для русского языка
RUSSIAN_STOP_WORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все",
    "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по",
    "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из",
    "ему", "теперь", "когда", "уже", "вам", "ним", "здесь", "тогда", "кто", "этот",
    "того", "потому", "этого", "какой", "совсем", "ней", "были", "нас", "них", "там",
    "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем", "была",
    "сам", "чтоб", "без", "будто", "человек", "чего", "раз", "тоже", "себе", "под",
    "жизнь", "будет", "ж", "тогда", "кого", "этой", "перед", "более", "через",
    "эти", "нас", "про", "всего", "них", "какая", "много", "разве", "сказала",
    "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой", "наконец", "два",
    "об", "другой", "хоть", "после", "над", "больше", "тот", "при", "должен", "это"
}

# Стоп-слова для английского языка
ENGLISH_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "been", "be", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
    "shall", "can", "need", "dare", "ought", "used", "i", "me", "my", "myself", "we",
    "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he",
    "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom",
    "this", "that", "these", "those", "am", "being", "having", "doing", "because",
    "until", "while", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "also"
}


def tokenize(text: str) -> List[str]:
    """
    Токенизирует текст, оставляя только слова.
    
    Args:
        text: Входной текст
        
    Returns:
        Список токенов (слов) в нижнем регистре
    """
    # Удаляем все кроме букв и пробелов, приводим к нижнему регистру
    text = text.lower()
    # Поддержка кириллицы и латиницы
    words = re.findall(r'[a-zа-яё]+', text)
    return words


def extract_keywords(
    text: str,
    top_n: int = 10,
    min_word_length: int = 3,
    language: Optional[str] = None
) -> List[Tuple[str, float]]:
    """
    Извлекает ключевые слова из текста на основе TF-IDF подхода.
    
    Используется упрощенный TF-IDF, где TF - частота слова в документе,
    а IDF аппроксимируется через длину слова (более длинные слова обычно более значимы).
    
    Args:
        text: Текст для анализа
        top_n: Количество возвращаемых ключевых слов
        min_word_length: Минимальная длина слова
        language: Язык текста ("ru", "en" или None для автоопределения)
        
    Returns:
        Список кортежей (слово, оценка) отсортированный по убыванию значимости
    """
    if not text or not text.strip():
        return []
    
    # Токенизация
    tokens = tokenize(text)
    
    if not tokens:
        return []
    
    # Автоопределение языка, если не задан
    if language is None:
        # Простая эвристика: если больше кириллических букв - русский
        cyrillic_count = sum(1 for t in tokens if re.match(r'^[а-яё]+$', t))
        language = "ru" if cyrillic_count > len(tokens) / 2 else "en"
    
    # Выбор стоп-слов
    stop_words = RUSSIAN_STOP_WORDS if language == "ru" else ENGLISH_STOP_WORDS
    
    # Фильтрация токенов
    filtered_tokens = [
        t for t in tokens 
        if len(t) >= min_word_length and t not in stop_words
    ]
    
    if not filtered_tokens:
        return []
    
    # Подсчет частоты (TF)
    word_freq = Counter(filtered_tokens)
    total_words = len(filtered_tokens)
    
    # Расчет оценки для каждого слова
    # Оценка = TF * log(длина слова + 1) - простая эвристика значимости
    word_scores = {}
    for word, count in word_freq.items():
        tf = count / total_words
        # Более длинные слова получают больший вес
        length_bonus = math.log(len(word) + 1)
        word_scores[word] = tf * length_bonus
    
    # Сортировка по оценке и возврат top_n
    sorted_keywords = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_keywords[:top_n]


def extract_keywords_simple(text: str, top_n: int = 10) -> List[str]:
    """
    Упрощенная версия - возвращает только список ключевых слов без оценок.
    
    Args:
        text: Текст для анализа
        top_n: Количество возвращаемых ключевых слов
        
    Returns:
        Список ключевых слов
    """
    keywords = extract_keywords(text, top_n=top_n)
    return [word for word, _ in keywords]
