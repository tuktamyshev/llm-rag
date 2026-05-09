# Платформа LLM RAG

Монолитное API-приложение на **FastAPI** для построения системы **Retrieval-Augmented Generation (RAG)**: загрузка данных из веба и Telegram, векторный поиск в **Qdrant**, переранжирование кросс-энкодером, ответы через **OpenRouter** (совместимый с OpenAI API). Есть основной веб-интерфейс на **React + Vite**, демо-клиент «киберразведка», офлайн-оценка качества через **RAGAS**, миграции схемы БД через **Alembic**.

---

## Содержание

1. [Возможности](#возможности)  
2. [Стек технологий](#стек-технологий)  
3. [Структура репозитория](#структура-репозитория)  
4. [Архитектура RAG](#архитектура-rag)  
5. [Быстрый старт (Docker)](#быстрый-старт-docker)  
6. [Локальный запуск без Docker](#локальный-запуск-без-docker)  
7. [Переменные окружения](#переменные-окружения)  
8. [Порты и сервисы](#порты-и-сервисы)  
9. [База данных и миграции](#база-данных-и-миграции)  
10. [API (кратко)](#api-кратко)  
11. [Конвейеры данных и запросов](#конвейеры-данных-и-запросов)  
12. [Оценка качества (RAGAS)](#оценка-качества-ragas)  
13. [Команды Makefile](#команды-makefile)  
14. [Известные ограничения и советы](#известные-ограничения-и-советы)  
15. [Telegram: настройка сбора](TELEGRAM_SETUP.md)

---

## Возможности

- **Пользователи и проекты**: регистрация, JWT, проекты с системным промптом.
- **Источники**: веб-страницы (URL), каналы/чаты **Telegram** (через Telethon).
- **Инжест**: сбор текста → очистка → рекурсивное чанкование → эмбеддинги → запись в Qdrant.
- **Чат с RAG**: история последних реплик в промпте, ответ с перечислением источников (chunk/source/score).
- **Переранжирование**: из векторного поиска берётся `top_k × RERANK_FETCH_MULTIPLIER` кандидатов, затем отбор **cross-encoder**.
- **Оценка**: скрипт `evaluation/ragas/run_eval.py` и библиотека **ragas** (метрики на основе LLM и эмбеддингов); запуск тех же метрик из UI (вкладка **RAGAS**).

Интерфейсы основного приложения и демо-примера ориентированы на **русский язык** (подписи, подсказки, сообщения об ошибках в UI).

---

## Стек технологий

| Область | Технологии |
|--------|------------|
| Backend | Python 3.11, FastAPI, Uvicorn, SQLAlchemy 2, Alembic |
| БД | PostgreSQL 16 |
| Векторы | Qdrant (образ `v1.12.6`), клиент `qdrant-client` 1.12–1.13 |
| Эмбеддинги | `sentence-transformers`, модель по умолчанию `ai-sage/Giga-Embeddings-instruct`, `transformers` 4.40–4.49, `einops` |
| Переранжирование | `sentence-transformers` CrossEncoder, по умолчанию `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM | OpenRouter через **httpx** (async-совместимый клиент в коде) |
| Скрапинг | `trafilatura`, `beautifulsoup4` |
| Telegram | `telethon` |
| Основной фронт | React, TypeScript, Vite |
| Демо UI | `examples/cyber_threat_ui` — React, Vite, Tailwind |
| Оценка | `ragas`, `langchain-openai` (обёртка LLM для судьи), при необходимости LangChain-эмбеддинги для метрик |

---

## Структура репозитория

```
llm-rag/
├── backend/                 # FastAPI-приложение, точка входа main.py
│   ├── api/v1/              # Маршруты API v1
│   ├── core/                # БД, настройки
│   ├── infrastructure/      # OpenRouter, коннекторы (web, telegram)
│   ├── modules/             # Доменные модули: users, projects, sources,
│   │                        # ingestion, embeddings, vectordb, rag, chat
│   └── alembic/             # Миграции Alembic
├── frontend/                # Основной UI (чат, проекты, источники)
├── examples/cyber_threat_ui/ # Демо: панель, новости, чат к API по project_id
├── evaluation/ragas/        # Сбор метрик RAGAS, CLI run_eval.py
├── requirements.txt         # Зависимости backend + eval
├── Dockerfile.backend
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Архитектура RAG

```
Вопрос пользователя
        │
        ▼
┌───────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ Chat Service  │────▶│ RAG Service         │────▶│ OpenRouter (LLM) │
│ + история     │     │ embed → search →    │     │                  │
│   диалога     │     │ rerank → prompt →   │     └──────────────────┘
└───────────────┘     │ generate            │              │
                      └─────────────────────┘              ▼
                               │                    Ответ + источники
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
    │ Giga-       │    │ Qdrant      │    │ Cross-       │
    │ Embeddings  │    │ (cosine)    │    │ Encoder      │
    └─────────────┘    └─────────────┘    └──────────────┘
```

---

## Быстрый старт (Docker)

Рекомендуется **Docker Engine** с плагином **Compose V2** (`docker compose`). Старая утилита `docker-compose` 1.x может давать ошибки с новыми образами.

### 1. Подготовка

```bash
cd llm-rag
cp .env.example .env
# Укажите OPENROUTER_API_KEY и при необходимости OPENROUTER_MODEL, JWT_SECRET
```

### 2. Запуск всего стека

```bash
docker compose up --build -d
# или
make up
```

Бэкенд собирается из `Dockerfile.backend`, поднимается с `network_mode: host`, поэтому обращается к PostgreSQL и Qdrant на **localhost** хоста с портами, проброшенными compose.

### 3. Проверка

- Документация API (Swagger): **http://localhost:8000/docs**  
- Основной фронт: **http://localhost:3000**  
- Демо Cyber Threat UI: **http://localhost:5175**  
- PostgreSQL: **localhost:5433** (в контейнере 5432)  
- Qdrant REST: **http://localhost:6333**

Первый запрос к чату может занять время: подгрузка модели эмбеддингов с Hugging Face и скачивание весов.

---

## Локальный запуск без Docker

Нужны **Python 3.11+**, **Node.js 20+**, локально запущенные **PostgreSQL** и **Qdrant** (версии согласуйте с `requirements.txt` и `docker-compose.yml`).

### Backend

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Выставьте DATABASE_URL на ваш Postgres, QDRANT_HOST/PORT, OPENROUTER_API_KEY

cd backend
alembic upgrade head   # или положитесь на автоподъём при старте приложения
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

При старте приложение пытается применить миграции Alembic; при ошибке возможен fallback на `create_all` (см. логи).

### Основной фронтенд

```bash
cd frontend
npm install
npm run dev
```

Переменная `VITE_API_URL` (см. `.env.example`) должна указывать на `http://localhost:8000/api/v1`.

### Демо cyber_threat_ui

```bash
cd examples/cyber_threat_ui
npm install
npm run dev
```

По умолчанию демо использует `VITE_RAG_API_URL` и `VITE_PROJECT_ID` из `.env` в корне примера или переменных окружения — для чата должен существовать проект с указанным ID в БД.

---

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните значения.

| Переменная | Назначение |
|------------|------------|
| `OPENROUTER_API_KEY` | **Обязательно** для генерации ответов и для RAGAS (судья). Ключ на [openrouter.ai](https://openrouter.ai). |
| `OPENROUTER_BASE_URL` | Базовый URL API, по умолчанию `https://openrouter.ai/api/v1`. |
| `OPENROUTER_MODEL` | Идентификатор модели (например `openai/gpt-4o-mini`). |
| `OPENROUTER_REFERER`, `OPENROUTER_APP_TITLE` | Заголовки для OpenRouter (по желанию). |
| `JWT_SECRET`, `JWT_EXPIRES_SECONDS` | Подпись и срок жизни JWT. |
| `CORS_ALLOW_ORIGINS` | Список origin через запятую для браузерных клиентов. |
| `DATABASE_URL` | Строка SQLAlchemy для Postgres, например `postgresql+psycopg2://user:pass@host:5432/llm_rag`. В Docker Compose для бэкенда хоста используется порт **5433**. |
| `QDRANT_HOST`, `QDRANT_PORT` | Хост и порт Qdrant. |
| `EMBEDDING_MODEL` | Модель для эмбеддингов, по умолчанию `ai-sage/Giga-Embeddings-instruct`. |
| `EMBEDDING_DEVICE` | `auto` (по умолчанию) / `cpu` / `cuda` / `cuda:0`. При `auto` — `cuda` если `torch.cuda.is_available()`, иначе `cpu`. В логах backend печатается строка `Embedding device: requested=… resolved=… cuda_available=…` — по ней проверяйте, что GPU действительно используется. |
| `EMBEDDING_BATCH_SIZE` | Размер батча для `model.encode` (по умолчанию `64`). На GPU имеет смысл увеличить. |
| `RERANK_ENABLED` | `true` / `false` — включить кросс-энкодер. |
| `RERANKER_MODEL` | Имя модели cross-encoder в Hugging Face. |
| `RERANKER_DEVICE` | Device для cross-encoder; по умолчанию наследует `EMBEDDING_DEVICE`. |
| `RERANK_FETCH_MULTIPLIER` | Сколько кандидатов запрашивать у Qdrant до rerank: `top_k × множитель`. |
| `RAGAS_COMPARE_USER_ID` | id пользователя в БД, от имени которого создаются временные проекты для RAGAS-сравнения (по умолчанию `1`). Этот пользователь должен существовать. |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | С [my.telegram.org](https://my.telegram.org) для инжеста Telegram. |
| `TELEGRAM_SESSION_NAME`, `TELEGRAM_MESSAGE_LIMIT`, `TELEGRAM_DAYS_BACK` | Сессия Telethon и лимиты сообщений. |
| `VITE_API_URL`, `VITE_RAG_API_URL`, `VITE_PROJECT_ID` | Для фронтендов (Vite): базовый URL API и ID проекта для демо. |

Для оценки RAGAS переменная **`RAGAS_EMBEDDING_MODEL`** задаёт модель эмбеддингов для метрик, где они нужны (по умолчанию `all-MiniLM-L6-v2`); см. `evaluation/ragas/metrics.py`. Для импорта `langchain_community.embeddings` может понадобиться пакет **`langchain-community`** (`pip install langchain-community`), если он не подтянулся транзитивно.

---

## Порты и сервисы

| Сервис | URL / порт | Примечание |
|--------|------------|------------|
| Backend | `http://localhost:8000` | `network_mode: host` в compose |
| Swagger | `/docs` | Интерактивная документация |
| Основной UI | `http://localhost:3000` | Контейнер `llm-rag-frontend` |
| Демо UI | `http://localhost:5175` | `llm-rag-example-ui` |
| PostgreSQL | `localhost:5433` | Пользователь/БД/пароль: см. `docker-compose.yml` |
| Qdrant | `localhost:6333` | gRPC: 6334 |

---

## База данных и миграции

- Схема описана моделями SQLAlchemy в `backend/modules/*/models.py`.
- Миграции: каталог `backend/alembic/`, конфиг `backend/alembic.ini` (путь к БД в `env.py`).

Применить вручную:

```bash
cd backend && alembic upgrade head
# или из корня:
make migrate
```

Создать новую ревизию (после изменения моделей):

```bash
make migration m="описание изменений"
```

---

## API (кратко)

Базовый префикс: **`/api/v1`**.

| Раздел | Примеры |
|--------|---------|
| Auth | `POST /auth/register`, `POST /auth/login` |
| Пользователи | `/users/...` |
| Проекты | `/projects/...` |
| Источники | `/sources/...` (web, telegram) |
| Инжест | `/ingestion/...` (обновление проекта, статистика) |
| RAG | `/rag/...` |
| Чат | `POST /chat/{project_id}`, `GET /chat/{project_id}/history` |
| Оценка RAGAS | `GET /evaluation/ragas-models`, `POST /evaluation/ragas`, `POST /evaluation/ragas-compare` (сравнение: `jsonl`, опционально `top_k`; временные проекты — см. раздел RAGAS), `POST /evaluation/ragas-compare-urls` (`urls`+`jsonl`: тот же compare, но временный индекс собирается из переданных URL) |

### Пример запроса чата

`POST /api/v1/chat/1`

```json
{
  "message": "Кратко опиши риски из базы знаний",
  "top_k": 5
}
```

Ответ:

```json
{
  "answer": "…",
  "sources": ["source_id=3, chunk_id=12, score=0.8732"]
}
```

Поле `query_embedding` в запросе опционально: если не передать, сервер сам посчитает эмбеддинг запроса той же моделью, что и при индексации.

---

## Конвейеры данных и запросов

### Инжест (загрузка в базу знаний)

1. **Сбор**: веб — `trafilatura` + `beautifulsoup4`; Telegram — `telethon`.  
2. **Очистка**: нормализация Unicode, удаление управляющих символов, схлопывание пробелов (`modules/ingestion/cleaning.py`).  
3. **Чанкование**: рекурсивное разбиение с разделителями абзацев/предложений (`chunking.py`).  
4. **Эмбеддинги**: батчевое кодирование, нормализация векторов для cosine similarity.  
5. **Qdrant**: upsert точек с payload (project_id, source_id, chunk_id, content).

### Запрос (RAG)

1. Эмбеддинг вопроса (та же модель).  
2. Поиск в Qdrant с фильтром по `project_id`, лимит `top_k × RERANK_FETCH_MULTIPLIER` при включённом rerank.  
3. Переранжирование cross-encoder, отбор top_k.  
4. Сборка промпта с историей диалога и контекстом (`prompt_builder.py`).  
5. Вызов LLM через OpenRouter.

---

## Оценка качества (RAGAS)

Установите зависимости из `requirements.txt`, задайте `OPENROUTER_API_KEY`, при необходимости модель судьи через `OPENROUTER_MODEL`.

Запуск из **корня репозитория** (чтобы пакет `evaluation` импортировался):

```bash
python -m evaluation.ragas.run_eval --dataset evaluation/sample_dataset.jsonl --output evaluation/results.json
```

То же можно сделать из **веб-интерфейса**: вкладка **RAGAS** → «Только RAGAS» (`POST /api/v1/evaluation/ragas`, полный JSONL) или **сравнение трёх веток** (`POST /api/v1/evaluation/ragas-compare`, тело `{"jsonl":"…","top_k":5}`):

1. **С RAG (standard)** — для каждой строки JSONL создаётся временный проект, `contexts` из строки чистится (`clean_text`) и режется рекурсивным сплиттером, эмбеддится, индексируется в Qdrant, далее retrieval + LLM по проекту.
2. **С RAG (raw)** — то же, но без очистки и с **наивным чанкованием** (фиксированное окно без оверлапа): эмулирует «нет предобработки».
3. **Без RAG** — тот же вопрос напрямую в LLM, без документов.

Каждая ветка оценивается RAGAS относительно **`ground_truth`** из строки. Все временные проекты после прогона удаляются (БД и Qdrant). Владелец временных проектов — пользователь из **`RAGAS_COMPARE_USER_ID`** (по умолчанию **`1`**, должен существовать в БД).

В UI выводятся также **тайминги и объёмы**: время «сбор + предобработка» и «векторизация» (по строкам и суммарно), размер сырого текста / после очистки / число и длина чанков, размерность вектора и общий объём векторов (float32). Видно, как «raw‑режим» отличается от стандартного по качеству и по стоимости обработки.

Те же метрики дублируются в **Docker‑логи бэкенда** (`docker compose logs backend`) — на каждый ингест одна структурированная строка вида:

```
INFO  [modules.ingestion.service] ingest[standard] project=37 source=51 type=web
  title='…' uri='…' | collect=0.963s clean=0.001s chunk=0.000s vectorize=101.256s total=102.219s
  | raw_chars=16666 cleaned_chars=16666 chunks=23 chunks_chars=18298
  | vector_dim=2048 vectors_size=184.0KiB
```

Логирование покрывает **все пути ингеста**: ручная загрузка/добавление источников, `refresh_project` (включая ручной/автоматический рефреш), фоновые scheduled‑джобы и оба RAGAS‑прогона (`ragas-compare`, `ragas-compare-urls`). По завершении compare в логе появляется ещё одна строка‑сводка на каждый режим (`ragas-compare[…/standard]`, `ragas-compare[…/raw]`).

Примеры JSONL: `frontend/public/ragas-sample.jsonl`, `ragas-ru-*.jsonl`. Бэкенд локально — с `PYTHONPATH=..` (см. `Makefile`, цель `backend`).

Формат **JSONL** (одна JSON-строка на пример):

```json
{"question": "…", "contexts": ["…"], "ground_truth": "…", "answer": "…"}
```

Для **`ragas-compare`** в каждой строке JSONL нужны **`question`**, **`ground_truth`** и **непустой список `contexts`** (по ним поднимается временный индекс для ветки с RAG). Поле **`answer`** не используется.

#### Свой пример: URL + вопросы

В UI вкладки RAGAS есть раскрывающийся блок **«Свой пример: задайте URL и вопросы»** (HTTP‑аналог — `POST /api/v1/evaluation/ragas-compare-urls`, тело `{"urls":[…], "jsonl":"…", "top_k":5}`). Логика:

- сервер скачивает каждую ссылку как обычный **WEB‑источник** (тот же конвейер, что и в проекте: trafilatura/BeautifulSoup);
- поднимаются **два временных проекта** (standard и raw), все URL индексируются в каждый;
- по всем вопросам из JSONL выполняется RAG (по двум проектам) и параллельно «без RAG» (прямой LLM);
- RAGAS считается к `ground_truth`; временные проекты удаляются.

В JSONL для этого режима достаточно полей `question` и `ground_truth` — `contexts` приходят с указанных URL. Ограничение — до **10 URL** за запуск (можно поменять в схеме).

Метрики настраиваются в `evaluation/ragas/metrics.py` (библиотека **ragas**; совместимость с версией `ragas` проверяйте при обновлении зависимостей).

---

## Команды Makefile

| Команда | Действие |
|---------|----------|
| `make help` | Список целей |
| `make up` | `docker compose up --build -d` |
| `make down` | Остановка контейнеров |
| `make logs` | Логи compose |
| `make ps` | Статус сервисов |
| `make backend` | Локально uvicorn из каталога `backend` |
| `make frontend` | `npm install && npm run dev` в `frontend` |
| `make example` | Демо в `examples/cyber_threat_ui` |
| `make migrate` | `alembic upgrade head` |
| `make migration m="текст"` | Автогенерация ревизии Alembic |
| `make eval` | Подсказка по запуску скрипта оценки |

---

## GPU для эмбеддингов и rerank

По умолчанию `EMBEDDING_DEVICE=auto` — на хостах с CUDA эмбеддинговая модель и cross-encoder поднимаются на GPU автоматически. Чтобы убедиться, что GPU реально используется, после старта backend смотрите логи:

```
Embedding device: requested=auto resolved=cuda | torch=2.x.x cuda_available=True gpus=1 ['NVIDIA GeForce RTX 4090']
Loading embedding model … on device=cuda …
Embedding model loaded – dimension=… device=cuda
```

Если видите `cuda_available=False` — установлен **CPU‑сборка `torch`** или GPU не проброшен в контейнер.

**Локально без Docker** (`make backend`): достаточно установить torch с поддержкой CUDA для вашей карты, например `pip install torch --index-url https://download.pytorch.org/whl/cu124`, и убедиться, что `python -c "import torch; print(torch.cuda.is_available())"` возвращает `True`.

**Docker**: установите [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), раскомментируйте блок `deploy.resources.reservations.devices` в `docker-compose.yml` (сервис `backend`) и пересоберите образ с CUDA‑совместимой версией `torch` (либо собирайте поверх образа `nvidia/cuda` / `pytorch/pytorch`). Кэш HuggingFace смонтирован в volume `hf_cache`, чтобы модели не перекачивались при каждом ребилде.

> Примечание: предустановленный `python:3.11-slim` ставит CPU‑версию `torch`. Для GPU соберите свой `Dockerfile.backend` поверх `pytorch/pytorch:*-cuda*-cudnn*-runtime` и не указывайте `torch` в `requirements.txt` (или укажите подходящий wheel).

---

## Известные ограничения и советы

1. **Версии Qdrant**: сервер и клиент `qdrant-client` должны быть согласованы (в проекте зафиксированы диапазоны в `requirements.txt` и образ в `docker-compose.yml`).  
2. **Модель Giga-Embeddings**: используется `transformers` 4.40–4.49 и зависимость `einops`; при смене версий `transformers` возможны несовместимости с кастомным кодом модели на Hugging Face.  
3. **OpenRouter**: бесплатные модели имеют лимиты; при `429` проверьте ключ, тариф и смену модели.  
4. **Первый запуск**: загрузка моделей с Hugging Face и прогрев embedding/reranker могут занять много времени и места на диске.  
5. **Telegram**: при первом обращении может потребоваться интерактивная авторизация сессии Telethon (в Docker это обычно настраивается отдельно).  
6. **Демо UI** обращается к API с браузера (localhost); при смене хостов обновите CORS и URL в переменных Vite.

---
