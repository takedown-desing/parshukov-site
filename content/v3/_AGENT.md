# Задание автору текстов v3 (общая часть)

Ты пишешь тексты страниц сайта дизайнера Вадима Паршукова (прототип v3, русский сайт).

Пути:
- Формат и правила (прочитать первым, целиком): /Users/alekseyborovikov/Documents/Work/claude/vadimporsh/parshukov-site/content/v3/_FORMAT.md
- Проверенные факты и тон: /Users/alekseyborovikov/Documents/Work/claude/vadimporsh/parshukov-site/v3/index.html (главная v3, читать тексты секций)
- SEO-структура страницы: /Users/alekseyborovikov/Documents/Work/claude/vadimporsh/seomachine/research/seo-ru/keywords-v2/structures/<slug>.md
- Бриф страницы с фактами: /Users/alekseyborovikov/Documents/Work/claude/vadimporsh/seomachine/research/seo-ru/keywords-v2/briefs/<slug>.md
  (если брифа нет, работай по структуре и фактам из _FORMAT.md)
- Результат: /Users/alekseyborovikov/Documents/Work/claude/vadimporsh/parshukov-site/content/v3/<slug>.md
- Проверка: cd /Users/alekseyborovikov/Documents/Work/claude/vadimporsh/parshukov-site && python3 tools/check_content.py <slug>.md …

Порядок для каждой страницы:
1. Прочитать структуру (она большая, читай частями, главное: ключевые запросы, H1/H2/H3, секции, FAQ, перелинковка, Meta)
   и бриф (факты, что запрещено говорить).
2. Написать файл строго в формате _FORMAT.md. Title/description/H1 из структуры, но с ценами из _FORMAT.md §4
   и без длинного тире.
3. Прогнать check_content.py. ОШИБКИ исправить все. «внимание» по объёму и длине title/description тоже поправить.
   «внимание» по цене: если цена не из разрешённого списка, убрать.
4. Перечитать текст глазами клиента-производственника: нет ли «мы», выдуманных цифр, канцелярита, повторов.

Ничего, кроме своих файлов в content/v3/, не создавать и не менять. Не трогать HTML, CSS, JS.

В конце ответь коротко (до 200 слов): список файлов с числом слов, какие непроверенные утверждения из
структуры/брифа выкинул (одной строкой на страницу, только существенные), открытые вопросы к Вадиму.
