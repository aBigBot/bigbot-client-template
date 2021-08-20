#!/bin/bash
 
set -e

#virtualenv -p python3 /env

#. /env/bin/activate

cd /app

/env/bin/python manage.py makemigrations
/env/bin/python manage.py migrate

export CREATE_SUPER_USER=$SUPERUSER:$SUPERUSER_PASSWORD

cat > create_superuser.sh <<EOF

if [[ -n "$CREATE_SUPER_USER" ]]; then
echo "==> Creating super user"

printf "from django.contrib.auth.models import User\nif not User.objects.exists(): User.objects.create_superuser(*'$CREATE_SUPER_USER'.split(':'))" | python manage.py shell
fi
EOF

bash create_superuser.sh

gunicorn -b :$PORT src.wsgi
