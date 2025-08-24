from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import zipfile
import tempfile
import time
import random
from datetime import datetime

from models import db, Client, Organization, ContractTemplate, TemplateFile
from utils import (
    normalize_url, clean_filename,
    should_include_template_name, create_simple_output_filename,
    ensure_unique_filename,
    enhanced_process_docx_template,
    process_docx_template_safe,
    create_output_filename_with_client_prefix,
    preserve_original_filename_with_prefix,
    smart_filename_generation
)


def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')

    # ===== МАРШРУТЫ ДЛЯ КЛИЕНТОВ =====

    @app.route('/clients')
    def clients():
        clients = Client.query.all()
        return render_template('clients.html', clients=clients)

    @app.route('/clients/add', methods=['GET', 'POST'])
    def add_client():
        if request.method == 'POST':
            client = Client(
                number=request.form['number'],
                full_name=request.form['full_name'],
                short_name=request.form['short_name'],
                inn=request.form['inn'],
                ogrn=request.form['ogrn'],
                address=request.form['address'],
                position=request.form['position'],
                position_genitive=request.form['position_genitive'],
                representative_name=request.form['representative_name'],
                representative_name_genitive=request.form['representative_name_genitive'],
                basis=request.form['basis'],
                bank_details=request.form['bank_details'],
                phone=request.form['phone'],
                email=request.form['email'],
                website=normalize_url(request.form['website'])
            )

            try:
                db.session.add(client)
                db.session.commit()
                flash('Клиент успешно добавлен!', 'success')
                return redirect(url_for('clients'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении клиента: {str(e)}', 'error')

        return render_template('add_client.html')

    @app.route('/clients/edit/<int:id>', methods=['GET', 'POST'])
    def edit_client(id):
        client = Client.query.get_or_404(id)

        if request.method == 'POST':
            client.number = request.form['number']
            client.full_name = request.form['full_name']
            client.short_name = request.form['short_name']
            client.inn = request.form['inn']
            client.ogrn = request.form['ogrn']
            client.address = request.form['address']
            client.position = request.form['position']
            client.position_genitive = request.form['position_genitive']
            client.representative_name = request.form['representative_name']
            client.representative_name_genitive = request.form['representative_name_genitive']
            client.basis = request.form['basis']
            client.bank_details = request.form['bank_details']
            client.phone = request.form['phone']
            client.email = request.form['email']
            client.website = normalize_url(request.form['website'])

            try:
                db.session.commit()
                flash('Клиент успешно обновлен!', 'success')
                return redirect(url_for('clients'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при обновлении клиента: {str(e)}', 'error')

        return render_template('edit_client.html', client=client)

    @app.route('/clients/delete/<int:id>')
    def delete_client(id):
        client = Client.query.get_or_404(id)
        try:
            db.session.delete(client)
            db.session.commit()
            flash('Клиент успешно удален!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении клиента: {str(e)}', 'error')

        return redirect(url_for('clients'))

    # ===== МАРШРУТЫ ДЛЯ ОРГАНИЗАЦИЙ =====

    @app.route('/organizations')
    def organizations():
        organizations = Organization.query.all()
        return render_template('organizations.html', organizations=organizations)

    @app.route('/organizations/add', methods=['GET', 'POST'])
    def add_organization():
        if request.method == 'POST':
            organization = Organization(
                signatory_position=request.form['signatory_position'],
                signatory_name=request.form['signatory_name'],
                signatory_power_of_attorney=request.form['signatory_power_of_attorney'],
                executor_position=request.form['executor_position'],
                executor_name=request.form['executor_name']
            )

            try:
                db.session.add(organization)
                db.session.commit()
                flash('Организация успешно добавлена!', 'success')
                return redirect(url_for('organizations'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении организации: {str(e)}', 'error')

        return render_template('add_organization.html')

    @app.route('/organizations/edit/<int:id>', methods=['GET', 'POST'])
    def edit_organization(id):
        organization = Organization.query.get_or_404(id)

        if request.method == 'POST':
            organization.signatory_position = request.form['signatory_position']
            organization.signatory_name = request.form['signatory_name']
            organization.signatory_power_of_attorney = request.form['signatory_power_of_attorney']
            organization.executor_position = request.form['executor_position']
            organization.executor_name = request.form['executor_name']

            try:
                db.session.commit()
                flash('Организация успешно обновлена!', 'success')
                return redirect(url_for('organizations'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при обновлении организации: {str(e)}', 'error')

        return render_template('edit_organization.html', organization=organization)

    @app.route('/organizations/delete/<int:id>')
    def delete_organization(id):
        organization = Organization.query.get_or_404(id)
        try:
            db.session.delete(organization)
            db.session.commit()
            flash('Организация успешно удалена!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении организации: {str(e)}', 'error')

        return redirect(url_for('organizations'))

    # ===== МАРШРУТЫ ДЛЯ ШАБЛОНОВ =====

    @app.route('/templates')
    def templates():
        templates = ContractTemplate.query.all()
        return render_template('templates.html', templates=templates)

    @app.route('/templates/upload', methods=['POST'])
    def upload_template():
        if 'files' not in request.files:
            flash('Файлы не выбраны', 'error')
            return redirect(url_for('templates'))

        files = request.files.getlist('files')
        template_name = request.form.get('name', '').strip()

        if not template_name:
            flash('Укажите название шаблона', 'error')
            return redirect(url_for('templates'))

        valid_files = []
        for file in files:
            if file.filename != '' and file.filename.endswith('.docx'):
                valid_files.append(file)

        if not valid_files:
            flash('Выберите хотя бы один файл .docx', 'error')
            return redirect(url_for('templates'))

        try:
            # Создаем новый шаблон
            template = ContractTemplate(
                name=template_name,
                description=request.form.get('description', '')
            )
            db.session.add(template)
            db.session.flush()  # Получаем ID шаблона

            # Сохраняем файлы
            for i, file in enumerate(valid_files):
                filename = secure_filename(file.filename)
                # Добавляем timestamp с микросекундами и случайное число для гарантии уникальности
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                random_suffix = random.randint(1000, 9999)
                unique_filename = f"{timestamp}_{random_suffix}_{i:02d}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

                file.save(filepath)

                # Создаем запись о файле
                template_file = TemplateFile(
                    template_id=template.id,
                    filename=unique_filename,
                    original_filename=filename
                )
                db.session.add(template_file)

                # Небольшая задержка для гарантии разных timestamp'ов
                time.sleep(0.01)

            db.session.commit()
            flash(f'Шаблон "{template_name}" успешно загружен с {len(valid_files)} файлами!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении шаблона: {str(e)}', 'error')

        return redirect(url_for('templates'))

    @app.route('/templates/delete/<int:id>')
    def delete_template(id):
        template = ContractTemplate.query.get_or_404(id)

        try:
            # Удаляем файлы с диска
            for template_file in template.files:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], template_file.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Удаляем из базы данных (файлы удаляются автоматически из-за cascade)
            db.session.delete(template)
            db.session.commit()
            flash('Шаблон успешно удален!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении шаблона: {str(e)}', 'error')

        return redirect(url_for('templates'))

    # ===== МАРШРУТЫ ДЛЯ ГЕНЕРАЦИИ ДОГОВОРОВ =====

    @app.route('/contracts')
    def contracts():
        clients = Client.query.all()
        organizations = Organization.query.all()
        templates = ContractTemplate.query.all()
        return render_template('contracts.html', clients=clients, organizations=organizations, templates=templates)

    @app.route('/contracts/generate', methods=['POST'])
    def generate_contracts():
        client_id = request.form['client_id']
        organization_id = request.form['organization_id']
        template_ids = request.form.getlist('template_ids')

        if not client_id or not organization_id or not template_ids:
            flash('Необходимо выбрать клиента, организацию и шаблоны', 'error')
            return redirect(url_for('contracts'))

        client = Client.query.get_or_404(client_id)
        organization = Organization.query.get_or_404(organization_id)
        templates = ContractTemplate.query.filter(ContractTemplate.id.in_(template_ids)).all()

        # Подготовка данных для замены
        data = {
            'Номер': client.number,
            'Полное_наименование': client.full_name,
            'Сокращенное_наименование': client.short_name,
            'ИНН': client.inn,
            'ОГРН': client.ogrn,
            'Адрес': client.address,
            'Должность': client.position,
            'Должность_р': client.position_genitive,
            'ФИО_представителя': client.representative_name,
            'ФИО_представителя_р': client.representative_name_genitive,
            'Основание': client.basis,
            'Реквизиты': client.bank_details,
            'Телефон': client.phone,
            'Электронная_почта': client.email,
            'Сайт': client.website,
            'Должность_подписанта': organization.signatory_position,
            'ФИО_подписанта': organization.signatory_name,
            'Доверенность_подписанта': organization.signatory_power_of_attorney,
            'Должность_исполнителя': organization.executor_position,
            'ФИО_исполнителя': organization.executor_name,
            'Дата': datetime.now().strftime('%d.%m.%Y')
        }

        # Создание временной папки для файлов
        with tempfile.TemporaryDirectory() as temp_dir:
            generated_files = []
            used_filenames = set()

            # Подготавливаем очищенное имя клиента для архива
            client_short = client.short_name or client.full_name
            clean_client_name = clean_filename(client_short)

            # Базовая временная метка для архива (одна для всех)
            archive_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            for template_idx, template in enumerate(templates):
                if not template.files:
                    continue

                for file_idx, template_file in enumerate(template.files):
                    template_path = os.path.join(app.config['UPLOAD_FOLDER'], template_file.filename)

                    if not os.path.exists(template_path):
                        flash(f'Файл шаблона не найден: {template_file.original_filename}', 'error')
                        continue

                    # Сохраняем оригинальное имя файла
                    output_filename = preserve_original_filename_with_prefix(
                        original_filename=template_file.original_filename,
                        client_name=clean_client_name,
                        template_name=template.name,
                        add_template=(len(templates) > 1)
                    )

                    # Обеспечиваем уникальность
                    final_filename = ensure_unique_filename(output_filename, used_filenames)
                    used_filenames.add(final_filename)
                    output_path = os.path.join(temp_dir, final_filename)

                    try:
                        # Используем улучшенную версию обработки
                        process_docx_template_safe(template_path, output_path, data)

                        # Проверяем, что файл действительно создан
                        if os.path.exists(output_path):
                            generated_files.append(output_path)
                        else:
                            flash(f'Не удалось создать файл для {template_file.original_filename}', 'error')

                    except Exception as e:
                        flash(
                            f'Ошибка при обработке файла {template_file.original_filename} из шаблона {template.name}: {str(e)}',
                            'error')
                        continue

            if generated_files:
                # Создание архива с базовой временной меткой
                archive_name = f"contracts_{clean_client_name}_{archive_timestamp}.zip"
                archive_path = os.path.join(app.config['OUTPUT_FOLDER'], archive_name)

                try:
                    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for file_path in generated_files:
                            file_name = os.path.basename(file_path)
                            zipf.write(file_path, file_name)

                    return send_file(archive_path, as_attachment=True, download_name=archive_name)

                except Exception as e:
                    flash(f'Ошибка при создании архива: {str(e)}', 'error')
                    return redirect(url_for('contracts'))
            else:
                flash('Не удалось создать ни одного договора. Проверьте шаблоны и данные.', 'error')
                return redirect(url_for('contracts'))

    @app.route('/cleanup/outputs')
    def cleanup_outputs():
        """Очистка папки с готовыми договорами"""
        try:
            import glob

            # Получаем все файлы в папке outputs
            files = glob.glob(os.path.join(app.config['OUTPUT_FOLDER'], '*'))
            deleted_count = 0

            for file_path in files:
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        continue

            if deleted_count > 0:
                flash(f'Удалено {deleted_count} файлов из папки готовых договоров', 'success')
            else:
                flash('Папка готовых договоров уже пуста', 'info')

        except Exception as e:
            flash(f'Ошибка при очистке папки: {str(e)}', 'error')

        return redirect(url_for('templates'))