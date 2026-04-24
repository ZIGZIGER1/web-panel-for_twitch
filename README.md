# Web panel by ZigZiger

Локальная web-панель для OBS и стрима.

Что это:
- панель управления сценой и персонажем;
- локальный прозрачный `Browser Source` для OBS;
- кастомный Twitch-чат;
- запуск без черного окна консоли, через системный трей.

## Запуск

### Из исходников

```powershell
py -m pip install -r requirements.txt
py mopsyan_sysan.py
```

Или просто запусти `start_mopsyan_sysan.bat`.

### Готовый файл

Собранный `exe` лежит в:

- `dist/Web_panel_by_ZigZiger.exe`
- `release/Web_panel_by_ZigZiger_portable.zip`

## Как использовать в OBS

1. Запусти панель.
2. Открой локальный адрес в браузере.
3. Скопируй URL сцены из панели и добавь его в OBS как `Browser Source`.
4. Если нужен отдельный чат, добавь chat URL вторым `Browser Source`.

## Картинки персонажа

- `1.png` — idle
- `2.png` и `3.png` — кадры речи

## Сборка exe

```powershell
py build_exe.py
```

Если `exe` уже собран и нужно только обновить portable-пакет:

```powershell
py build_exe.py --package-only
```

## Что есть в репозитории

- `web/` — интерфейс панели
- `assets/ui/` — графика интерфейса
- `web_runtime.py` — локальный runtime и сервер
- `scene_renderer.py` — рендер сцены
- `chat_overlay.py` — чат и overlay
- `mopsyan_tray.py` — запуск через трей

В репозиторий не добавляются `build/`, `dist/`, `release/` и временные файлы.
