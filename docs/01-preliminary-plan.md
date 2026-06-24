# Kie AI Desktop — предварительный план

> Версия: 0.2 (с ответами заказчика)  
> Дата: 22.06.2026  
> Статус: ожидает уточнений от заказчика

---

## 1. Вводные от заказчика

### 1.1 Цель проекта

Нативное **desktop-приложение** для работы с платформой [kie.ai](https://kie.ai) — единым API-доступом к LLM, генерации изображений и видео.

### 1.2 Функциональные вкладки

| Вкладка | Функции |
|---------|---------|
| **Чаты** | Окно чата/переписки с моделями, выбор модели, история чатов |
| **Изображения** | Галерея сгенерированных материалов; чат/окно новой генерации; выбор моделей (у каждой модели — свои параметры) |
| **Видео** | Аналогично вкладке «Изображения» |
| **Настройки** | Тема и интерфейс; ввод API-ключа; вкл/выкл уведомления о завершении генерации; опциональный лимит генерации |

### 1.3 Общие требования (все вкладки)

- Отображение **актуального баланса** аккаунта/API
- У каждой модели — **ценник** (стоимость генерации)
- После генерации — показ **итога потраченных токенов/кредитов**

### 1.4 Технологический контекст

- Frontend: выбор между **Tauri/Rust**, **C#**, **Go** или альтернативой; приоритет — современный UI
- Backend: вероятно **Python**, но не окончательно
- Окружение разработки: **Windows 11**, РФ (возможны сетевые ограничения — прокси на уровне приложения)

---

## 2. Справка по API kie.ai (актуальная документация)

Источники: [docs.kie.ai](https://docs.kie.ai), [Getting Started](https://docs.kie.ai/1973359m0.md), [Market](https://docs.kie.ai/market/quickstart.md), [Common API](https://docs.kie.ai/common-api/quickstart.md).

### 2.1 Базовые параметры

| Параметр | Значение |
|----------|----------|
| Base URL | `https://api.kie.ai` |
| Аутентификация | `Authorization: Bearer <API_KEY>` |
| Content-Type | `application/json` |
| Каталог моделей | [kie.ai/market](https://kie.ai/market) |
| Прайс-лист | [kie.ai/pricing](https://kie.ai/pricing) |
| Логи задач | [kie.ai/logs](https://kie.ai/logs) |

### 2.2 Два типа API-потоков

**A. Чат-модели (синхронные / streaming)**

- Прямые эндпоинты по провайдеру, например:
  - Claude: `POST /claude/v1/messages`
  - GPT/Gemini: аналогичные chat-completions эндпоинты
- Поддержка **SSE streaming** (`stream: true`)
- В ответе: `usage` (input/output tokens) и **`credits_consumed`**
- Оплата: по токенам

**B. Генерация медиа (асинхронные задачи)**

- Создание: `POST /api/v1/jobs/createTask` с полями `model`, `input`, опционально `callBackUrl`
- Ответ: `taskId` (HTTP 200 ≠ задача завершена)
- Статус: `GET /api/v1/jobs/recordInfo?taskId={taskId}` (polling)
- Альтернатива polling: webhook `callBackUrl` + [верификация подписи](https://docs.kie.ai/common-api/webhook-verification.md)
- Некоторые модели (Veo, 4o Image, Flux Kontext, Runway) имеют **собственные** эндпоинты — нужен адаптер по типу модели

### 2.3 Баланс и файлы

| Эндпоинт | Назначение |
|----------|------------|
| `GET /api/v1/chat/credit` | Текущий баланс кредитов (`data: number`) |
| `POST /api/v1/common/download-url` | Временная ссылка на скачивание (TTL **20 минут**) |
| File Upload API | Загрузка референсов для image-to-video / edit |

### 2.4 Важные ограничения для desktop-приложения

| Ограничение | Влияние на дизайн |
|-------------|-------------------|
| Медиа хранятся **14 дней** на сервере | Локальное кэширование галереи обязательно |
| Логи — **2 месяца** | История задач — дублировать локально |
| Rate limit: **20 запросов / 10 сек** | Очередь задач, backoff при 429 |
| Код **402** — нет кредитов | Проверка баланса перед генерацией |
| API-ключ **нельзя** светить в клиентском JS | Ключ только в backend/sidecar или secure storage Tauri |
| Ссылки на скачивание — 20 мин | Скачивать и сохранять локально сразу после генерации |

### 2.5 Ориентировочная стоимость (из Market docs)

- Изображения: ~10–50 кредитов за генерацию
- Видео: ~100–500 кредитов
- LLM: по токенам (`credits_consumed` в ответе)

Точные цены — с [kie.ai/pricing](https://kie.ai/pricing); в приложении нужен механизм обновления прайса (ручной конфиг / парсинг / API, если появится).

---

## 3. Предлагаемая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop Shell (Tauri / др.)                 │
│  ┌──────────┬──────────┬──────────┬──────────┐  Balance bar │
│  │  Чаты    │ Изображ. │  Видео   │ Настройки│  (всегда)   │
│  └──────────┴──────────┴──────────┴──────────┘              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              UI Layer (React + TypeScript)               │ │
│  │  Chat UI │ Gallery │ Generation Panel │ Settings Forms   │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ IPC (Tauri commands / localhost)
┌──────────────────────────▼──────────────────────────────────┐
│                     Application Core                           │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────────┐ │
│  │ KieClient   │ │ TaskManager  │ │ LocalStore (SQLite)    │ │
│  │ (HTTP)      │ │ poll/queue   │ │ chats, gallery, settings│ │
│  └─────────────┘ └──────────────┘ └────────────────────────┘ │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────────┐ │
│  │ ModelRegistry│ │ PricingCache │ │ NotificationService    │ │
│  │ (schemas)   │ │              │ │ (OS toast)             │ │
│  └─────────────┘ └──────────────┘ └────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS (+ optional proxy)
                    ┌──────▼──────┐
                    │  api.kie.ai │
                    └─────────────┘
```

### 3.1 Ключевые модули backend/core

1. **KieClient** — единый HTTP-клиент с прокси, retry, обработкой кодов 401/402/429/501
2. **ModelRegistry** — каталог моделей с JSON Schema параметров (из OpenAPI docs.kie.ai)
3. **TaskManager** — очередь async-задач, polling с exponential backoff, уведомления по завершении
4. **LocalStore** — SQLite: чаты, сообщения, метаданные генераций, пути к локальным файлам
5. **PricingService** — кэш цен; отображение «от X кредитов» до генерации и факт после
6. **SecureSettings** — API-ключ в OS keychain (Windows Credential Manager через Tauri plugin)

---

## 4. Сравнение технологий для desktop UI

### 4.1 Критерии оценки

| Критерий | Вес для проекта |
|----------|-----------------|
| Современный UI / дизайн-системы | Высокий |
| Размер бинарника и RAM | Средний |
| Скорость разработки UI | Высокий |
| Интеграция с Python backend | Средний |
| Нативные уведомления Windows | Средний |
| Кроссплатформенность | Низкий–средний (пока Windows) |
| Безопасность API-ключа | Высокий |

### 4.2 Tauri 2 + React/Vue + TypeScript

| Плюсы | Минусы |
|-------|--------|
| Маленький бинарник (~5–15 MB vs 150+ MB Electron) | Нужен Rust для shell (или минимальный) |
| Web-стек: Tailwind, shadcn/ui, Radix — современный UI «из коробки» | WebView2 на Windows (зависимость от Edge) |
| Tauri plugins: keychain, notifications, fs, HTTP | SSE/streaming через IPC требует продуманной архитектуры |
| Можно вызывать Python sidecar как child process | Два языка в проекте при Python backend |
| Активное сообщество, Tauri 2 стабилен | |

### 4.3 C# (WinUI 3 / WPF / Avalonia)

| Плюсы | Минусы |
|-------|--------|
| Нативный Windows look & feel (WinUI 3) | WinUI 3 — сложнее кроссплатформенность |
| Отличная интеграция с Windows APIs | UI «корпоративный» без усилий — менее «современный» |
| Avalonia — кроссплатформа, XAML | Меньше готовых AI/chat UI компонентов |
| Один язык для shell + можно встроить Python через процесс | Дизайн-системы слабее чем React-экосистема |

### 4.4 Go (Wails / Fyne)

| Плюсы | Минусы |
|-------|--------|
| Wails — аналог Tauri (Go + WebView) | Fyne UI ограничен для «богатого» chat UX |
| Один бинарник, быстрая сборка | Меньше UI-библиотек уровня shadcn |
| Хорош для HTTP/горутин polling | Python backend — отдельный процесс |

### 4.5 Альтернативы

| Стек | Когда имеет смысл |
|------|-------------------|
| **Electron + React** | Максимум готовых npm-пакетов; минус — тяжёлый runtime |
| **Flutter Desktop** | Единый UI-код; chat/gallery хорошо; слабее Windows-native feel |
| **.NET MAUI** | Если команда уже на C#; UI средний |
| **Tauri + Rust core (без Python)** | Меньше moving parts; HTTP в Rust (reqwest) |

### 4.6 Предварительная рекомендация

**Основной вариант: Tauri 2 + React + TypeScript + Tailwind/shadcn**

- UI: максимальная свобода для современного дизайна (чат, галерея, masonry grid, видеоплеер)
- Core: **Python sidecar** (FastAPI или чистый asyncio) *или* логика в **Rust** внутри Tauri — решение после уточнения компетенций команды
- Если Python не нужен: весь backend на Rust в Tauri — проще деплой, один installer

**Запасной вариант (Windows-only, .NET-команда):** Avalonia UI + C# core + Python subprocess при необходимости.

---

## 5. Детализация вкладок (черновик UX)

### 5.1 Глобальный header

```
[Logo] Kie AI Desktop          Баланс: 1 234 кр. ↻    [⚙]
```

- Периодическое обновление баланса (каждые 30–60 сек + после каждой операции)
- Клик по балансу → детализация / ссылка на пополнение (kie.ai)

### 5.2 Чаты

```
┌─────────────┬──────────────────────────────────────┐
│ История     │  [Claude Sonnet 4.6 ▼]  ~0.25 кр/1K  │
│ чатов       │──────────────────────────────────────│
│ + Новый     │  Сообщения (markdown, code blocks)   │
│             │──────────────────────────────────────│
│             │  [Ввод...]              [Отправить]  │
└─────────────┴──────────────────────────────────────┘
```

- Streaming ответов (SSE)
- После ответа: `input_tokens`, `output_tokens`, `credits_consumed`
- История в SQLite; экспорт чата (опционально, v2)

### 5.3 Изображения / Видео (единый паттерн)

```
┌─────────────┬──────────────────────────────────────┐
│ Галерея     │  [Kling 2.6 T2V ▼]  ~200 кр/ген.    │
│ (сетка)     │  Параметры модели (динамическая     │
│             │  форма из ModelRegistry)             │
│ Фильтры     │──────────────────────────────────────│
│             │  Промпт / референсы                  │
│             │  [Генерировать]  Статус: в очереди…  │
└─────────────┴──────────────────────────────────────┘
```

- Галерея: локальные превью + метаданные (модель, кредиты, дата)
- Генерация: progress bar / статус polling
- По завершении: toast (если включено), показ результата, запись `credits_consumed` из `recordInfo`
- Автоскачивание файла в `%AppData%/KieAI/media/`

### 5.4 Настройки

| Секция | Параметры |
|--------|-----------|
| API | Ключ (masked), тест подключения, прокси URL (HTTP/SOCKS5) |
| Интерфейс | Тема: light / dark / system; язык UI: ru / en |
| Уведомления | Вкл/выкл OS toast при завершении генерации |
| Лимиты | Опционально: max кредитов за сессию / за день; предупреждение при пороге |
| Хранилище | Путь к локальной галерее; очистка кэша |

---

## 6. Модель данных (локально)

```sql
-- Упрощённая схема
settings (key, value_encrypted)
chats (id, title, model_id, created_at, updated_at)
messages (id, chat_id, role, content, tokens_in, tokens_out, credits, created_at)
generations (id, type, model_id, task_id, status, prompt, params_json,
             credits_used, remote_url, local_path, created_at, completed_at)
models_cache (id, category, name, schema_json, price_hint, updated_at)
credit_snapshots (id, balance, recorded_at)
```

---

## 7. Этапы реализации (roadmap)

| Фаза | Содержание | Результат |
|------|------------|-----------|
| **0. Discovery** | Уточнение требований, выбор стека, прототип API-клиента | Этот документ v1.0 |
| **1. Foundation** | Scaffold Tauri + UI shell, настройки, API-ключ, баланс | Запускается окно, виден баланс |
| **2. Chats** | 1–2 chat-модели, streaming, история | Рабочий чат |
| **3. Images** | ModelRegistry, createTask, polling, галерея | Генерация изображений |
| **4. Video** | Расширение registry, видеоплеер | Генерация видео |
| **5. Polish** | Уведомления, лимиты, прокси, ошибки, автообновление прайса | MVP release |

---

## 8. Риски и митигации

| Риск | Митигация |
|------|-----------|
| Блокировка api.kie.ai из РФ | Настраиваемый HTTP/SOCKS5 прокси в настройках |
| Много моделей с разными API | ModelRegistry + адаптеры по `category` + unified jobs API где возможно |
| Устаревание прайса | Периодический refresh; fallback на kie.ai/pricing |
| Потеря медиа через 14 дней | Автоскачивание при успешной генерации |
| Утечка API-ключа | Keychain + запрет логирования ключа |

---

## 9. Открытые решения

~~См. вопросы к заказчику в разделе 10. После ответов документ обновится до **v1.0**.~~

**Обновлено по ответам заказчика (22.06.2026) — см. раздел 11.**

---

## 10. Ссылки

- [Документация kie.ai](https://docs.kie.ai)
- [Индекс API (llms.txt)](https://docs.kie.ai/llms.txt)
- [Market Quickstart](https://docs.kie.ai/market/quickstart.md)
- [Common API](https://docs.kie.ai/common-api/quickstart.md)
- [Pricing](https://kie.ai/pricing)
- [Tauri 2](https://v2.tauri.app/)

---

## 11. Решения заказчика (v0.2)

| Вопрос | Решение |
|--------|---------|
| Платформа | **Только Windows 11** |
| Стек UI | **Tauri 2 + React + TypeScript** (согласовано 22.06.2026) |
| Backend | **Гибрид**: UI-логика в shell, API/polling/БД в Python |
| MVP — модели | **Минимум**: 1–2 chat, 2–3 image, 1–2 video |
| Чат MVP | Streaming, multimodal (vision), function calling/tools, папки для чатов |
| Галерея | **Только локально** сохранённые файлы |
| Лимит генерации | **Макс. кредитов за сессию** приложения |
| Аудио (Suno и др.) | **Фаза 2**, после MVP |
| Язык UI | **RU + EN** (переключатель) |
| Прокси | **HTTP/HTTPS/SOCKS5 в настройках с первого дня** (согласовано) |
| Дизайн | **Современный glassmorphism** с акцентами |

### 11.1 Финальная рекомендация стека (при гибридном backend)

Учитывая: Windows-only, glass-modern UI, Python для тяжёлой логики, минимальный MVP — рекомендуется:

```
┌─────────────────────────────────────────┐
│  Tauri 2  +  React  +  TypeScript       │  ← UI, i18n, glass-дизайн
│  Tailwind CSS + shadcn/ui + framer-motion│
└──────────────────┬──────────────────────┘
                   │ IPC (localhost / Tauri sidecar)
┌──────────────────▼──────────────────────┐
│  Python 3.12+ sidecar                   │  ← KieClient, TaskManager,
│  httpx (async) + SQLite + pydantic      │    ModelRegistry, SSE proxy
└──────────────────┬──────────────────────┘
                   │ HTTPS (+ proxy из настроек)
            api.kie.ai
```

**Почему не C#/Go/Electron:**

| Вариант | Вердикт |
|---------|---------|
| C# WinUI/Avalonia | Слабее экосистема для chat UI + glass-дизайна; Python sidecar всё равно нужен |
| Go Wails | UI-библиотеки беднее React; дублирование с Python |
| Electron | Избыточный вес (~150 MB) без выигрыша при Windows-only |
| Tauri + Rust-only core | Отказ от Python усложнит итерации по ModelRegistry из OpenAPI docs |

**Почему Tauri + React + Python sidecar:**

- React-экосистема: готовые chat-компоненты, markdown, code highlight, drag-drop для multimodal
- Tauri: нативные уведомления Windows, keychain для API-ключа, лёгкий installer
- Python: быстрая интеграция с десятками эндпоинтов kie.ai, asyncio polling, Pydantic-схемы из OpenAPI
- Sidecar упаковывается в один `.exe` через Tauri `externalBin`

### 11.2 Уточнённый MVP scope

**Чаты (выбрать 1–2):**

- Claude Sonnet 4.6 (`/claude/v1/messages`) — streaming, tools, `credits_consumed`
- GPT 5.2 или Gemini 3 Flash — multimodal (image input)

**Изображения (2–3):**

- Flux-2 Text to Image (`jobs/createTask`)
- GPT Image / Nano Banana — по популярности на market

**Видео (1–2):**

- Kling 2.6 Text to Video
- Seedance / Veo — один на выбор

**Не в MVP:** вкладка Аудио, синхронизация с kie.ai/logs, экспорт чатов (можно v1.1).

### 11.3 Дополнения к UX из ответов

- **Папки чатов**: дерево/список слева, drag-and-drop между папками (v1.1 если не влезет в MVP)
- **Multimodal**: загрузка изображения в чат → File Upload API kie.ai → URL в `messages.content`
- **Лимит сессии**: счётчик `session_credits_spent`; при достижении порога — блокировка генерации + диалог
- **i18n**: `react-i18next`, ключи `ru` / `en`
- **Glass UI**: полупрозрачные панели, blur-backdrop, акцентный градиент; тёмная тема по умолчанию + light option в настройках

| Дизайн | **Современный glassmorphism** с акцентами |

### 11.4 Архитектура

Детальный документ: **[02-architecture.md](./02-architecture.md)** (v1.0, согласовано).

