<?php
$root = __DIR__;
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$ext = strtolower(pathinfo($uri, PATHINFO_EXTENSION));
$isDocument = $uri === '/' || in_array($ext, ['html','php'], true) || $ext === '';
if ($isDocument) {
    require_once $root . '/api/db.php';
    // Every document/API page load attempts pending schema migrations.
    // Public pages still render if MySQL is offline; authenticated API endpoints report the DB error themselves.
    schema_status();
}
if ($uri === '/') {
    readfile($root . '/index.html');
    return true;
}
$path = realpath($root . $uri);
if ($path && str_starts_with($path, realpath($root)) && is_file($path)) return false;
http_response_code(404);
echo 'Not found';
return true;
