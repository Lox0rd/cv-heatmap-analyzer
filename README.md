# Interest Heatmap

Программа для построения тепловых карт зон интереса на основе анализа видеоданных.

## Требования

- Python 3.10+
- Git
- OpenCV
- API-ключ CometAPI для работы с Vision API

## Установка

Клонировать репозиторий:

```bash
git clone https://github.com/Lox0rd/cv-heatmap-analyzer
cd cv-heatmap-analyzer
```

Создать виртуальное окружение:

```bash
python -m venv .venv
```

Активировать его:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

## Настройка API

Создать файл `.env` в корне проекта:

```env
COMET_API_KEY=your_api_key_here
COMET_BASE_URL=https://api.cometapi.com/v1
VISION_MODEL=qwen-vl-plus
```

API-ключ не следует добавлять в Git.

## Запуск

Запустить программу:

```bash
python main.py
```

Входные видео помещаются в:

```text
data/input/
```

Результаты работы сохраняются в:

```text
data/output/
```

## Структура проекта

```text
interest-heatmap/
├── main.py
├── src/
│   ├── config/       # Конфигурация
│   ├── detection/    # Обнаружение и отслеживание объектов
│   ├── video/        # Обработка видео
│   ├── heatmap/      # Построение тепловых карт
│   ├── zones/        # Работа с зонами
│   ├── analysis/     # Анализ данных
│   ├── ai/           # Работа с Vision API
│   ├── export/       # Экспорт результатов
│   └── gui/          # Графический интерфейс
├── models/           # Модели YOLO
├── data/
│   ├── input/        # Входные файлы
│   └── output/       # Результаты
├── tests/            # Тесты
├── requirements.txt
└── .env
```

## Важно

Не добавляйте файл `.env` в репозиторий. Для этого он должен находиться в `.gitignore`.

Для новых настроек используйте `.env.example`.