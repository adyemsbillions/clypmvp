<?php
require_once __DIR__ . '/env.php';

function clyp_config(): array {
    static $cfg = null;
    if ($cfg === null) $cfg = require __DIR__ . '/config.php';
    return $cfg;
}

function db_server(): PDO {
    static $pdo = null;
    if ($pdo instanceof PDO) return $pdo;
    $d = clyp_config()['db'];
    $dsn = "mysql:host={$d['host']};port={$d['port']};charset=utf8mb4";
    $pdo = new PDO($dsn, $d['user'], $d['pass'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    return $pdo;
}

function quote_mysql_identifier(string $identifier): string {
    if ($identifier === '' || strlen($identifier) > 64 || !preg_match('/^[A-Za-z0-9_$-]+$/', $identifier)) {
        throw new RuntimeException('Invalid MySQL identifier: ' . $identifier);
    }
    return '`' . str_replace('`', '``', $identifier) . '`';
}

function ensure_database_exists(): void {
    $d = clyp_config()['db'];
    $database = quote_mysql_identifier($d['name']);
    db_server()->exec("CREATE DATABASE IF NOT EXISTS {$database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
}


function db(): PDO {
    static $pdo = null;
    if ($pdo instanceof PDO) return $pdo;
    ensure_database_exists();
    $d = clyp_config()['db'];
    $dsn = "mysql:host={$d['host']};port={$d['port']};dbname={$d['name']};charset=utf8mb4";
    $pdo = new PDO($dsn, $d['user'], $d['pass'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    return $pdo;
}

function split_sql_statements(string $sql): array {
    $sql = preg_replace('/^\s*--.*$/m', '', $sql);
    $parts = preg_split('/;\s*(?:\r?\n|$)/', $sql) ?: [];
    return array_values(array_filter(array_map('trim', $parts), fn($s) => $s !== ''));
}

function ensure_schema(): array {
    $pdo = db();
    $pdo->exec("CREATE TABLE IF NOT EXISTS schema_migrations (
        migration VARCHAR(190) PRIMARY KEY,
        applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

    $dir = dirname(__DIR__) . '/database/migrations';
    $files = glob($dir . '/*.sql') ?: [];
    sort($files, SORT_NATURAL);
    $applied = [];
    foreach ($files as $file) {
        $name = basename($file);
        $q = $pdo->prepare('SELECT migration FROM schema_migrations WHERE migration=?');
        $q->execute([$name]);
        if ($q->fetchColumn()) continue;
        $sql = file_get_contents($file);
        if ($sql === false) throw new RuntimeException("Cannot read migration {$name}");
        foreach (split_sql_statements($sql) as $statement) $pdo->exec($statement);
        $i = $pdo->prepare('INSERT INTO schema_migrations(migration,applied_at) VALUES(?,NOW())');
        $i->execute([$name]);
        $applied[] = $name;
    }
    return $applied;
}

function schema_status(): array {
    try {
        $applied = ensure_schema();
        return ['ok' => true, 'database' => clyp_config()['db']['name'], 'applied' => $applied];
    } catch (Throwable $e) {
        return ['ok' => false, 'message' => $e->getMessage()];
    }
}

function require_schema(): void {
    try {
        ensure_schema();
    } catch (Throwable $e) {
        json_out(['ok'=>false,'message'=>'MySQL/schema setup failed: '.$e->getMessage()], 503);
    }
}

function json_input(): array {
    $raw = file_get_contents('php://input');
    if (!$raw) return [];
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : [];
}

function json_out(array $data, int $status=200): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function session_user_id(): ?int {
    if (session_status() !== PHP_SESSION_ACTIVE) session_start();
    return isset($_SESSION['user_id']) ? (int)$_SESSION['user_id'] : null;
}

function require_user_id(): int {
    $id = session_user_id();
    if (!$id) json_out(['ok'=>false,'message'=>'Unauthenticated'], 401);
    return $id;
}

function http_post_json(string $url, array $payload, array $headers = [], int $timeout = 60): array {
    $body = json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    $headers = array_merge(['Content-Type: application/json'], $headers);
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $body,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $timeout,
        ]);
        $raw = curl_exec($ch);
        $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        if ($raw === false) return ['status'=>0,'body'=>'','error'=>$err ?: 'HTTP request failed'];
        return ['status'=>$status,'body'=>$raw,'error'=>null];
    }
    $ctx = stream_context_create(['http'=>[
        'method'=>'POST',
        'header'=>implode("\r\n", $headers),
        'content'=>$body,
        'timeout'=>$timeout,
        'ignore_errors'=>true,
    ]]);
    $raw = @file_get_contents($url, false, $ctx);
    $status = 0;
    if (!empty($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m)) $status = (int)$m[1];
    return ['status'=>$status,'body'=>$raw === false ? '' : $raw,'error'=>$raw === false ? 'HTTP request failed' : null];
}
