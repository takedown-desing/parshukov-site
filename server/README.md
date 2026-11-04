# Свой сервер (play2go, 31.77.11.175)

Доступ: `seomachine/наше агенство/server.env`. На сервере работают парсеры (`/opt/job-parser`, `/opt/maps-parser`,
порты 43251 и 7777): их не трогать.

| Что | Где на сервере |
|---|---|
| Сайт (содержимое `dist/`) | `/var/www/parshukov-site/` |
| nginx | `/etc/nginx/sites-available/parshukov-site` (копия `server/nginx.conf`) |
| Настройки форм | `/etc/parshukov-site/form.env`, root:www-data 640 (образец `server/form.env.example`) |
| Ошибки отправки | `journalctl -u php8.5-fpm`, `/var/log/nginx/error.log` |

## Выкладка

```bash
python3 tools/build_v3.py && python3 tools/check_content.py
python3 tools/export_prod.py --site-url https://parkovagency.com --index   # без --index сайт закрыт от поисковиков
rsync -az --delete dist/ root@31.77.11.175:/var/www/parshukov-site/
```

`--delete` чистит только папку сайта. `form.env` лежит вне неё и при выкладке не меняется.

## Подключение домена

1. DNS у регистратора: A `@` и A `www` на `31.77.11.175`.
2. В `nginx.conf` вписать `server_name ДОМЕН www.ДОМЕН;`, затем `certbot --nginx -d ДОМЕН -d www.ДОМЕН --redirect`.
3. `ALLOWED_HOSTS=ДОМЕН,www.ДОМЕН` в `form.env`.
4. Экспорт с `--site-url https://ДОМЕН --index`, выкладка, sitemap в Вебмастер и Search Console.

## Защита форм

Ловушка `website`, отправка не раньше 3 секунд после загрузки страницы, проверка Origin, nginx пропускает
6 заявок в минуту с одного IP. Яндекс SmartCaptcha включается двумя ключами: серверный в `form.env`
(`SMARTCAPTCHA_SERVER_KEY`), клиентский флагом `--captcha` при экспорте.
