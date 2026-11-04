<?php
// Приём заявок со всех форм сайта: проверка, защита от ботов, письмо через SMTP.
// Заявки нигде не сохраняются: данные только пересылаются на почту из настроек.
// Настройки: /etc/parshukov-site/form.env (образец в server/form.env.example).

declare(strict_types=1);

use PHPMailer\PHPMailer\PHPMailer;

const CONFIG = '/etc/parshukov-site/form.env';
const MIN_ELAPSED_MS = 3000;  // быстрее человек форму не заполнит
const MAX_BODY = 32768;
const MAX_FIELD = 4000;

const LABELS = [
    'name' => 'Имя', 'company' => 'Компания', 'phone' => 'Телефон', 'email' => 'Email',
    'channel' => 'Удобный способ связи', 'need' => 'Что нужно', 'budget' => 'Бюджет', 'message' => 'Задача',
    'project' => 'Проект', 'services' => 'Услуги', 'total' => 'Итого', 'term' => 'Срок', 'payment' => 'Оплата',
    'discount' => 'Скидка за предоплату', 'source' => 'Источник', 'page' => 'Страница',
];

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function reply(int $code, array $body): never
{
    http_response_code($code);
    echo json_encode($body, JSON_UNESCAPED_UNICODE);
    exit;
}

function config(): array
{
    $cfg = [];
    foreach (@file(CONFIG, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [] as $line) {
        if ($line[0] === '#' || !str_contains($line, '=')) continue;
        [$k, $v] = explode('=', $line, 2);
        $cfg[trim($k)] = trim($v);
    }
    return $cfg;
}

function one_line(string $s, int $max): string
{
    return mb_substr(trim(preg_replace('/[\r\n\t]+/', ' ', $s)), 0, $max);
}

// Ответ ботам: «принято», но письмо не отправляем, чтобы не подсказывать, что их поймали
function drop(): never
{
    reply(200, ['ok' => true]);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') reply(405, ['ok' => false, 'error' => 'method']);

$cfg = config();

// Чужие сайты не должны слать заявки через наш обработчик
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin !== '') {
    $hosts = array_filter(array_map('trim', explode(',', $cfg['ALLOWED_HOSTS'] ?? '')));
    $hosts[] = $_SERVER['HTTP_HOST'] ?? '';
    if (!in_array(parse_url($origin, PHP_URL_HOST), $hosts, true)) reply(403, ['ok' => false, 'error' => 'origin']);
}

$raw = file_get_contents('php://input', false, null, 0, MAX_BODY + 1);
if ($raw === false || strlen($raw) > MAX_BODY) reply(413, ['ok' => false, 'error' => 'size']);
$data = json_decode($raw, true);
if (!is_array($data) || count($data) > 40) reply(400, ['ok' => false, 'error' => 'format']);

// Ловушка: поле website скрыто от людей, его заполняют только боты
if (trim((string)($data['website'] ?? '')) !== '') drop();
// Время на странице до отправки, считает скрипт сайта
if ((int)($data['_elapsed'] ?? 0) < MIN_ELAPSED_MS) drop();

// Яндекс SmartCaptcha, если в настройках есть серверный ключ
$captchaKey = $cfg['SMARTCAPTCHA_SERVER_KEY'] ?? '';
if ($captchaKey !== '') {
    $token = (string)($data['_captcha'] ?? '');
    if ($token === '') reply(400, ['ok' => false, 'error' => 'captcha']);
    $ch = curl_init('https://smartcaptcha.yandexcloud.net/validate');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query(['secret' => $captchaKey, 'token' => $token,
                                                'ip' => $_SERVER['REMOTE_ADDR'] ?? '']),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 5,
    ]);
    $resp = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    // Если сервис капчи недоступен, заявку не теряем (так советует документация Яндекса)
    if ($httpCode === 200 && (json_decode((string)$resp, true)['status'] ?? '') !== 'ok') {
        reply(400, ['ok' => false, 'error' => 'captcha']);
    }
}

// Поля письма: служебные (с подчёркиванием) и ловушку не показываем
$rows = [];
foreach ($data as $k => $v) {
    if (!is_string($k) || $k === '' || $k[0] === '_' || $k === 'website' || $k === 'consent') continue;
    if (is_array($v)) $v = implode(', ', array_map('strval', array_filter($v, 'is_scalar')));
    elseif (is_bool($v)) $v = $v ? 'да' : 'нет';
    elseif (!is_scalar($v)) continue;
    $v = mb_substr(trim((string)$v), 0, MAX_FIELD);
    if ($v === '') continue;
    $rows[LABELS[$k] ?? one_line($k, 40)] = $v;
}

$email = trim((string)($data['email'] ?? ''));
$emailOk = $email !== '' && filter_var($email, FILTER_VALIDATE_EMAIL);
$digits = preg_match_all('/\d/', (string)($data['phone'] ?? ''));
if (!$emailOk && ($digits < 10 || $digits > 15)) reply(400, ['ok' => false, 'error' => 'contact']);

foreach (['MAIL_TO', 'SMTP_HOST', 'SMTP_FROM'] as $k) {
    if (($cfg[$k] ?? '') === '') {
        error_log("send.php: в настройках не заполнено $k");
        reply(503, ['ok' => false, 'error' => 'config']);
    }
}

require '/usr/share/php/libphp-phpmailer/autoload.php';

$subject = one_line((string)($data['_subject'] ?? ''), 150) ?: 'Заявка с сайта';
$html = '<table cellpadding="6" cellspacing="0" border="1" style="border-collapse:collapse;font:14px Arial,sans-serif">';
$text = '';
foreach ($rows as $label => $v) {
    $html .= '<tr><th align="left" valign="top" style="background:#f5f5f5">' . htmlspecialchars($label) . '</th><td>'
           . nl2br(htmlspecialchars($v)) . '</td></tr>';
    $text .= "$label: $v\n";
}
$html .= '</table>';

$m = new PHPMailer(true);
try {
    $m->isSMTP();
    $m->Host = $cfg['SMTP_HOST'];
    $m->Port = (int)($cfg['SMTP_PORT'] ?? 465);
    $secure = $cfg['SMTP_SECURE'] ?? 'ssl';
    $m->SMTPSecure = $secure === 'ssl' ? PHPMailer::ENCRYPTION_SMTPS : ($secure === 'tls' ? PHPMailer::ENCRYPTION_STARTTLS : '');
    $m->SMTPAutoTLS = $secure !== 'none';
    $m->SMTPAuth = ($cfg['SMTP_USER'] ?? '') !== '';
    $m->Username = $cfg['SMTP_USER'] ?? '';
    $m->Password = $cfg['SMTP_PASS'] ?? '';
    $m->Timeout = 15;
    $m->CharSet = PHPMailer::CHARSET_UTF8;
    $m->setFrom($cfg['SMTP_FROM'], $cfg['SMTP_FROM_NAME'] ?? 'Сайт');
    foreach (array_filter(array_map('trim', explode(',', $cfg['MAIL_TO']))) as $to) $m->addAddress($to);
    if ($emailOk) $m->addReplyTo($email);
    $m->Subject = $subject;
    $m->isHTML(true);
    $m->Body = $html;
    $m->AltBody = $text;
    $m->send();
} catch (Throwable $e) {
    error_log('send.php: письмо не ушло: ' . $m->ErrorInfo);
    reply(502, ['ok' => false, 'error' => 'mail']);
}

reply(200, ['ok' => true]);
