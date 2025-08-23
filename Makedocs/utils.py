import os
import re
import hashlib
from docx import Document


def replace_placeholders(text, data):
    """Заменяет плейсхолдеры в тексте на данные"""
    if not text:
        return text

    for key, value in data.items():
        placeholder = '{{ ' + key + ' }}'
        if placeholder in text:
            text = text.replace(placeholder, str(value or ''))
    return text


def normalize_url(url):
    """Нормализует URL, добавляя протокол если необходимо"""
    if not url:
        return url

    url = url.strip()
    if url and not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url


def clean_filename(filename):
    """Очищает имя файла от недопустимых символов, сохраняя читаемость"""
    # Убираем расширение
    name_without_ext = os.path.splitext(filename)[0] if '.' in filename else filename
    # Заменяем недопустимые символы на подчеркивания
    clean_name = re.sub(r'[<>:"/\\|?*]', '_', name_without_ext)
    # Убираем лишние пробелы и подчеркивания
    clean_name = re.sub(r'[_\s]+', '_', clean_name).strip('_')
    return clean_name if clean_name else 'document'


def simple_replace_in_paragraph(paragraph, data):
    """Безопасная замена плейсхолдеров в параграфе с улучшенной обработкой ошибок"""
    if not paragraph or not hasattr(paragraph, 'runs'):
        return False

    # Проверяем наличие runs
    if not paragraph.runs:
        return False

    # Получаем весь текст параграфа
    full_text = paragraph.text
    if not full_text or '{{' not in full_text:
        return False

    # Заменяем плейсхолдеры
    original_text = full_text
    for key, value in data.items():
        placeholder = '{{ ' + key + ' }}'
        if placeholder in full_text:
            full_text = full_text.replace(placeholder, str(value or ''))

    # Если изменений не было
    if full_text == original_text:
        return False

    # Безопасная замена: проверяем наличие runs
    try:
        if len(paragraph.runs) > 0:
            # Сохраняем форматирование первого run'а
            first_run = paragraph.runs[0]
            first_run.text = full_text

            # Очищаем остальные runs (в обратном порядке, чтобы не сбить индексы)
            for i in range(len(paragraph.runs) - 1, 0, -1):
                try:
                    paragraph.runs[i].text = ""
                except IndexError:
                    # Пропускаем, если индекс уже недоступен
                    continue

            return True
        else:
            # Если нет runs, создаем новый
            run = paragraph.add_run(full_text)
            return True

    except Exception as e:
        print(f"Ошибка при замене в параграфе: {e}")
        # Попробуем создать новый run с текстом
        try:
            # Очищаем все существующие runs
            for run in paragraph.runs:
                run.text = ""
            # Добавляем новый run с замененным текстом
            paragraph.add_run(full_text)
            return True
        except Exception as e2:
            print(f"Критическая ошибка при создании run: {e2}")
            return False


def process_docx_template_safe(template_path, output_path, data):
    """Безопасная версия обработки DOCX с улучшенной обработкой таблиц"""
    try:
        print(f"📄 Открытие файла: {template_path}")
        doc = Document(template_path)

        replacements_made = 0

        # Обработка основного текста
        print("🔍 Поиск плейсхолдеров в основном тексте...")
        for i, paragraph in enumerate(doc.paragraphs):
            try:
                if simple_replace_in_paragraph(paragraph, data):
                    replacements_made += 1
                    print(f"  ✅ Замена в параграфе {i}")
            except Exception as e:
                print(f"  ⚠️ Ошибка в параграфе {i}: {e}")
                continue

        # ❗ ИСПРАВЛЕННАЯ ОБРАБОТКА ТАБЛИЦ
        print("🔍 Поиск плейсхолдеров в таблицах...")
        print(f"   Найдено таблиц: {len(doc.tables)}")

        for table_idx, table in enumerate(doc.tables):
            print(f"   📊 Обработка таблицы {table_idx + 1}")
            try:
                # Получаем размеры таблицы
                rows_count = len(table.rows)
                print(f"      Строк в таблице: {rows_count}")

                for row_idx, row in enumerate(table.rows):
                    try:
                        cells_count = len(row.cells)
                        print(f"      Строка {row_idx + 1}: ячеек {cells_count}")

                        for cell_idx, cell in enumerate(row.cells):
                            try:
                                # Получаем весь текст ячейки
                                cell_text = cell.text

                                if '{{' in cell_text:
                                    print(f"        Ячейка [{row_idx + 1}][{cell_idx + 1}] содержит плейсхолдеры:")
                                    print(f"          Текст: '{cell_text[:100]}...'")

                                    # Обрабатываем все параграфы в ячейке
                                    cell_replacements = 0
                                    for para_idx, paragraph in enumerate(cell.paragraphs):
                                        if '{{' in paragraph.text:
                                            print(f"          Параграф {para_idx}: '{paragraph.text}'")

                                            if simple_replace_in_paragraph(paragraph, data):
                                                cell_replacements += 1
                                                replacements_made += 1
                                                print(f"          ✅ Замена выполнена: '{paragraph.text}'")

                                    if cell_replacements == 0:
                                        print(f"          ⚠️ Замены не выполнены в ячейке")

                                        # Попробуем альтернативный метод для проблемных ячеек
                                        if alternative_cell_replacement(cell, data):
                                            replacements_made += 1
                                            print(f"          ✅ Альтернативная замена выполнена")

                            except Exception as e:
                                print(f"        ⚠️ Ошибка в ячейке [{row_idx + 1}][{cell_idx + 1}]: {e}")
                                continue

                    except Exception as e:
                        print(f"      ⚠️ Ошибка в строке {row_idx + 1}: {e}")
                        continue

            except Exception as e:
                print(f"    ⚠️ Ошибка в таблице {table_idx + 1}: {e}")
                continue

        # Обработка заголовков и футеров
        print("🔍 Поиск плейсхолдеров в заголовках и футерах...")
        for section_idx, section in enumerate(doc.sections):
            try:
                # Заголовки
                if hasattr(section, 'header') and section.header:
                    for para_idx, paragraph in enumerate(section.header.paragraphs):
                        try:
                            if simple_replace_in_paragraph(paragraph, data):
                                replacements_made += 1
                                print(f"  ✅ Замена в заголовке секции {section_idx}")
                        except Exception as e:
                            print(f"  ⚠️ Ошибка в заголовке секции {section_idx}[{para_idx}]: {e}")
                            continue

                # Футеры
                if hasattr(section, 'footer') and section.footer:
                    for para_idx, paragraph in enumerate(section.footer.paragraphs):
                        try:
                            if simple_replace_in_paragraph(paragraph, data):
                                replacements_made += 1
                                print(f"  ✅ Замена в футере секции {section_idx}")
                        except Exception as e:
                            print(f"  ⚠️ Ошибка в футере секции {section_idx}[{para_idx}]: {e}")
                            continue
            except Exception as e:
                print(f"  ⚠️ Ошибка в секции {section_idx}: {e}")
                continue

        print(f"📊 Всего замен выполнено: {replacements_made}")

        if replacements_made == 0:
            print("⚠️  ВНИМАНИЕ: Ни одного плейсхолдера не найдено!")
            print("Проверьте формат плейсхолдеров в документе. Должно быть: {{ Имя_переменной }}")

            # Показываем содержимое для отладки
            print("\n📋 Отладочная информация:")

            # Показываем таблицы
            for table_idx, table in enumerate(doc.tables):
                print(f"  Таблица {table_idx + 1}:")
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        if cell.text.strip():
                            print(f"    [{row_idx + 1}][{cell_idx + 1}]: {cell.text[:200]}")

        # Сохраняем документ
        doc.save(output_path)
        print(f"💾 Документ сохранен: {output_path}")

        return True

    except Exception as e:
        print(f"❌ Критическая ошибка при обработке документа: {e}")
        import traceback
        traceback.print_exc()
        raise e


def alternative_cell_replacement(cell, data):
    """Альтернативный метод замены в ячейке таблицы"""
    try:
        # Получаем весь текст ячейки
        cell_text = cell.text

        if not cell_text or '{{' not in cell_text:
            return False

        # Выполняем замены в тексте
        modified_text = cell_text
        for key, value in data.items():
            placeholder = '{{ ' + key + ' }}'
            if placeholder in modified_text:
                modified_text = modified_text.replace(placeholder, str(value or ''))

        # Если изменений не было
        if modified_text == cell_text:
            return False

        # Очищаем ячейку и добавляем новый текст
        cell.clear()
        paragraph = cell.paragraphs[0]  # После clear() остается один пустой параграф
        paragraph.add_run(modified_text)

        print(f"        🔄 Альтернативная замена: '{cell_text[:50]}...' → '{modified_text[:50]}...'")
        return True

    except Exception as e:
        print(f"        ❌ Ошибка альтернативной замены: {e}")
        return False


def analyze_table_structure(template_path):
    """Анализ структуры таблиц в документе"""
    try:
        doc = Document(template_path)

        print(f"\n📊 АНАЛИЗ ТАБЛИЦ В ДОКУМЕНТЕ: {template_path}")
        print("=" * 60)

        for table_idx, table in enumerate(doc.tables):
            print(f"\n🔍 Таблица {table_idx + 1}:")
            print(f"   Строк: {len(table.rows)}")

            for row_idx, row in enumerate(table.rows):
                print(f"   Строка {row_idx + 1}: {len(row.cells)} ячеек")

                for cell_idx, cell in enumerate(row.cells):
                    cell_text = cell.text.strip()
                    if cell_text:
                        print(
                            f"     Ячейка [{row_idx + 1}][{cell_idx + 1}]: '{cell_text[:100]}{'...' if len(cell_text) > 100 else ''}'")

                        # Проверяем плейсхолдеры
                        if '{{' in cell_text:
                            import re
                            placeholders = re.findall(r'\{\{[^}]*\}\}', cell_text)
                            print(f"       🎯 Плейсхолдеры: {placeholders}")

        return True

    except Exception as e:
        print(f"❌ Ошибка анализа таблиц: {e}")
        return False


def diagnose_document_placeholders(template_path):
    """Диагностика плейсхолдеров в документе"""
    try:
        doc = Document(template_path)
        placeholders_found = set()

        # Поиск в основном тексте
        for paragraph in doc.paragraphs:
            text = paragraph.text
            # Ищем все плейсхолдеры в формате {{ text }}
            matches = re.findall(r'\{\{\s*([^}]+)\s*\}\}', text)
            for match in matches:
                placeholders_found.add(match.strip())

        # Поиск в таблицах
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        text = paragraph.text
                        matches = re.findall(r'\{\{\s*([^}]+)\s*\}\}', text)
                        for match in matches:
                            placeholders_found.add(match.strip())

        # Поиск в заголовках и футерах
        for section in doc.sections:
            if hasattr(section, 'header') and section.header:
                for paragraph in section.header.paragraphs:
                    text = paragraph.text
                    matches = re.findall(r'\{\{\s*([^}]+)\s*\}\}', text)
                    for match in matches:
                        placeholders_found.add(match.strip())

            if hasattr(section, 'footer') and section.footer:
                for paragraph in section.footer.paragraphs:
                    text = paragraph.text
                    matches = re.findall(r'\{\{\s*([^}]+)\s*\}\}', text)
                    for match in matches:
                        placeholders_found.add(match.strip())

        return list(placeholders_found)

    except Exception as e:
        print(f"Ошибка диагностики: {e}")
        return []


def calculate_file_hash(file_path):
    """Вычисляет хэш файла для проверки уникальности"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Ошибка при вычислении хэша файла {file_path}: {e}")
        return "error"


def debug_file_contents(file_path, max_chars=500):
    """Показывает начало содержимого файла для отладки"""
    try:
        doc = Document(file_path)
        text_content = []

        # Собираем текст из первых нескольких параграфов
        for i, paragraph in enumerate(doc.paragraphs[:5]):
            if paragraph.text.strip():
                text_content.append(f"П{i}: {paragraph.text[:100]}...")

        content_preview = " | ".join(text_content)
        return content_preview[:max_chars] if content_preview else "Нет текстового содержимого"
    except Exception as e:
        return f"Ошибка чтения: {e}"


def debug_template_processing(templates, template_ids):
    """Отладочная функция для анализа выбранных шаблонов"""
    print(f"\n🔍 ОТЛАДКА ШАБЛОНОВ:")
    print(f"   Получено ID шаблонов: {template_ids}")
    print(f"   Найдено шаблонов в БД: {len(templates)}")

    for i, template in enumerate(templates):
        print(f"\n   📋 Шаблон #{i + 1}:")
        print(f"      ID: {template.id}")
        print(f"      Название: '{template.name}'")
        print(f"      Описание: '{template.description or 'Не указано'}'")
        print(f"      Дата создания: {template.created_at}")
        print(f"      Количество файлов: {len(template.files)}")

        for j, template_file in enumerate(template.files):
            file_path = os.path.join('uploads/templates', template_file.filename)
            file_exists = os.path.exists(file_path)
            file_size = os.path.getsize(file_path) if file_exists else 0
            file_hash = calculate_file_hash(file_path) if file_exists else "N/A"

            print(f"         📄 Файл #{j + 1}:")
            print(f"            ID в БД: {template_file.id}")
            print(f"            Оригинал: {template_file.original_filename}")
            print(f"            Система: {template_file.filename}")
            print(f"            Существует: {'✅' if file_exists else '❌'}")
            print(f"            Размер: {file_size} байт")
            print(f"            MD5: {file_hash}")
            print(f"            Загружен: {template_file.uploaded_at}")

            # Проверяем уникальность файлов
            if file_exists:
                try:
                    content_preview = debug_file_contents(file_path, 100)
                    print(f"            Содержимое: {content_preview}")
                except Exception as e:
                    print(f"            Ошибка чтения: {e}")

        # Проверяем, есть ли дублирующиеся хэши в одном шаблоне
        file_hashes = []
        for template_file in template.files:
            file_path = os.path.join('uploads/templates', template_file.filename)
            if os.path.exists(file_path):
                file_hash = calculate_file_hash(file_path)
                file_hashes.append((template_file.original_filename, file_hash))

        # Проверяем дубликаты
        seen_hashes = set()
        duplicates = []
        for filename, hash_val in file_hashes:
            if hash_val in seen_hashes:
                duplicates.append(filename)
            seen_hashes.add(hash_val)

        if duplicates:
            print(f"      ⚠️ НАЙДЕНЫ ДУБЛИРУЮЩИЕСЯ ФАЙЛЫ: {duplicates}")
        else:
            print(f"      ✅ Все файлы уникальны")