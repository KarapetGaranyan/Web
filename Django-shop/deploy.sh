#!/bin/bash

# Скрипт развертывания Django проекта на сервер
# Использование: ./deploy.sh your-username your-domain.com

if [ $# -ne 2 ]; then
    echo "Использование: $0 <username> <domain>"
    echo "Пример: $0 ubuntu mysite.com"
    exit 1
fi

USERNAME=$1
DOMAIN=$2
PROJECT_DIR="/home/$USERNAME/django-shop-asset"

echo "🚀 Начинаем развертывание Django проекта..."
echo "Пользователь: $USERNAME"
echo "Домен: $DOMAIN"
echo "Директория проекта: $PROJECT_DIR"

# Создаем директории для логов
sudo mkdir -p /var/log/django-shop
sudo mkdir -p /var/log/nginx

# Устанавливаем права на директории
sudo chown -R $USERNAME:www-data /var/log/django-shop
sudo chmod -R 755 /var/log/django-shop

# Переходим в директорию проекта
cd $PROJECT_DIR

# Активируем виртуальное окружение
source venv/bin/activate

# Применяем миграции
echo "📦 Применяем миграции..."
python manage.py migrate --settings=shop.settings_production

# Собираем статические файлы
echo "📁 Собираем статические файлы..."
python manage.py collectstatic --settings=shop.settings_production --noinput

# Заполняем базу тестовыми данными
echo "🗄️ Заполняем базу тестовыми данными..."
python populate_db.py --settings=shop.settings_production

# Настраиваем права доступа
echo "🔐 Настраиваем права доступа..."
sudo chown -R $USERNAME:www-data $PROJECT_DIR
sudo chmod -R 755 $PROJECT_DIR
sudo chmod 664 $PROJECT_DIR/db.sqlite3

# Копируем конфигурацию Supervisor
echo "⚙️ Настраиваем Supervisor..."
sudo cp django-shop.conf /etc/supervisor/conf.d/
sudo sed -i "s/your-username/$USERNAME/g" /etc/supervisor/conf.d/django-shop.conf

# Копируем конфигурацию Nginx
echo "🌐 Настраиваем Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/django-shop
sudo sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/django-shop
sudo sed -i "s/your-username/$USERNAME/g" /etc/nginx/sites-available/django-shop

# Активируем сайт в Nginx
sudo ln -sf /etc/nginx/sites-available/django-shop /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Перезапускаем сервисы
echo "🔄 Перезапускаем сервисы..."
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart django-shop
sudo systemctl restart nginx

# Проверяем статус
echo "✅ Проверяем статус сервисов..."
sudo supervisorctl status django-shop
sudo systemctl status nginx

echo "🎉 Развертывание завершено!"
echo "🌐 Ваш сайт доступен по адресу: http://$DOMAIN"
echo "🔧 Админ-панель: http://$DOMAIN/admin/"
echo "📊 Логи Django: /var/log/django-shop/"
echo "📊 Логи Nginx: /var/log/nginx/django-shop.*.log" 