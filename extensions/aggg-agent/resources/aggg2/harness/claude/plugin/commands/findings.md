---
description: Поиск находок и выводов ресёрча в research.db (findings.py search)
argument-hint: запрос (2-4 слова)
---
Найди в базе знаний AGGG2.0 выводы по теме «$ARGUMENTS»:
`python3 db-tools/findings.py search "$ARGUMENTS"` (корень AGGG2.0 —
маркер VERSION или $AGGG2_ROOT). Если пусто — попробуй короче/другими
словами (склонения ловит триграм: `search.py --substring`). Дай ответ:
id находки, дата, тема, суть вывода. Если не нашлось — честно скажи.
