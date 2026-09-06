
Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->

# C. АРХИТЕКТУРА И ПРОСТОТА

YAGNI, модули по причине изменений, shared core (21-30)

# C. АРХИТЕКТУРА И ПРОСТОТА

---

## 21. YAGNI UNTIL SECOND NEED
**Принцип:** Абстракция с одним потребителем — долг, не архитектура.
**Правило:** Inline until second implementation; тогда extract.
**Антипаттерн:** AbstractRepository + одна SqliteRepo «на вырост».
**Проверка:** Можно удалить слой — поведение то же, кода меньше.

---

## 22. STD LIB / PLATFORM BEFORE DEPENDENCY
**Принцип:** Новая зависимость дороже 30 строк своего кода (часто).
**Правило:** Сначала stdlib/native; dep только если боль измерима.
**Антипаттерн:** moment.js ради одного format; ORM ради 5 SQL.
**Проверка:** package.json/requirements растут медленнее фич.

---

## 23. SEPARATE MODULES BY CHANGE REASON
**Принцип:** Промпты/экспорт/платежи/хендлеры меняются по-разному.
**Правило:** generators.py, cryptopay.py, access.py, bot.py — разные оси.
**Антипаттерн:** 3000-line god file «bot.py does everything».
**Проверка:** Фича PDF не требует трогать billing.

---

## 24. SHARED CORE, THIN ADAPTERS
**Принцип:** Бизнес-логика одна; Telegram/CLI/desktop — оболочка.
**Правило:** voice router общий; bot только I/O + auth + UX.
**Антипаттерн:** Скопировали STT в бот «чтобы быстрее».
**Проверка:** Баг в polish чинится в одном месте, оба клиента ок.

---

## 25. CONFIG OUTSIDE REPO, DEFAULTS IN CODE
**Принцип:** Секреты и ops-тюнинг не в git; безопасные default'ы в коде.
**Правило:** secrets.env вне проекта; FREE_MINUTES=30 default; override env.
**Антипаттерн:** Токен в репо; магические числа без имени.
**Проверка:** clone без secrets не утекает ключами; тесты monkeypatch env.

---

## 26. SCHEMA EVOLUTION MUST NOT WIPE PROD
**Принцип:** Деплой новой версии не требует DROP TABLE.
**Правило:** CREATE IF NOT EXISTS + ALTER ADD COLUMN ignore-if-exists.
**Антипаттерн:** «Пересоздай БД» как инструкция релиза.
**Проверка:** Старый файл БД открывается новым кодом.

---

## 27. EXPLICIT SPEND/PRIORITY ORDER IN ONE FUNCTION
**Принцип:** Порядок списания — один алгоритм, не размазан.
**Правило:** charge(): free → bonus → paid в одном месте.
**Антипаттерн:** Часть в handler, часть в SQL trigger «как получится».
**Проверка:** Тест на каждый переход границы bucket'а.

---

## 28. CACHE BY STABLE KEY, REBUILD VIEWS
**Принцип:** Дорогое (LLM) кэшировать; дешёвое (сбор PDF) пересобирать.
**Правило:** PK (entity_id, kind); export всегда из cache+source.
**Антипаттерн:** Кэш PDF на диске устаревает при новом артефакте.
**Проверка:** Второй клик generate = 0 external calls.

---

## 29. CALLBACK/API MINI-PROTOCOL
**Принцип:** Короткие префиксы + версионируемые поля > свободный JSON в кнопке.
**Правило:** hl:page, ho:id:back; regex router; back_context всегда с собой.
**Антипаттерн:** callback_data = целый JSON без схемы; Back теряет страницу.
**Проверка:** Deep navigation возвращает на тот же list offset.

---

## 30. FALLBACK CHAIN FOR PROVIDERS
**Принцип:** Один вендор = single point of failure.
**Правило:** ordered list; next on timeout/5xx; fail only when all dead.
**Антипаттерн:** hardcode one API; outage = full downtime.
**Проверка:** Mock first provider down → second succeeds.

---



Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
