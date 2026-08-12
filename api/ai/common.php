<?php
require_once __DIR__ . '/../db.php';

function ai_limits(int $uid): array {
    $pdo = db();
    $q = $pdo->prepare('SELECT plan FROM users WHERE id=?');
    $q->execute([$uid]);
    $plan = $q->fetchColumn() ?: 'free';
    return match ($plan) {
        'pro' => ['plan'=>'pro','designs'=>30,'edits'=>30],
        'single' => ['plan'=>'single','designs'=>1,'edits'=>0],
        default => ['plan'=>'free','designs'=>3,'edits'=>3],
    };
}

function current_usage(int $uid): array {
    $period = date('Y-m-01');
    $q = db()->prepare('SELECT ai_generations_used,ai_edits_used FROM usage_monthly WHERE user_id=? AND period_start=?');
    $q->execute([$uid,$period]);
    return $q->fetch() ?: ['ai_generations_used'=>0,'ai_edits_used'=>0];
}

function assert_ai_quota(int $uid, string $kind): void {
    $limits = ai_limits($uid);
    $usage = current_usage($uid);
    $used = $kind === 'edit' ? (int)$usage['ai_edits_used'] : (int)$usage['ai_generations_used'];
    $limit = $kind === 'edit' ? $limits['edits'] : $limits['designs'];
    if ($used >= $limit) json_out(['ok'=>false,'message'=>'Your '.$kind.' allowance is finished for this plan.','code'=>'usage_limit','plan'=>$limits['plan']], 402);
}

function increment_ai_usage(int $uid, string $kind): void {
    $period = date('Y-m-01');
    $field = $kind === 'edit' ? 'ai_edits_used' : 'ai_generations_used';
    $sql = "INSERT INTO usage_monthly(user_id,period_start,{$field}) VALUES(?,?,1) ON DUPLICATE KEY UPDATE {$field}={$field}+1";
    db()->prepare($sql)->execute([$uid,$period]);
}

function call_python_ai(string $route, array $payload): array {
    $cfg = clyp_config();
    $url = rtrim($cfg['ai']['endpoint'], '/') . '/' . ltrim($route, '/');
    $started = microtime(true);
    $result = http_post_json($url, $payload, ['X-Internal-Token: '.$cfg['ai']['internal_token']], 90);
    $duration = (int)round((microtime(true)-$started)*1000);
    $decoded = json_decode($result['body'] ?? '', true);
    return [
        'ok' => $result['status'] >= 200 && $result['status'] < 300 && is_array($decoded) && ($decoded['ok'] ?? false),
        'status' => $result['status'],
        'data' => is_array($decoded) ? $decoded : null,
        'duration_ms' => $duration,
        'error' => $result['error'] ?? null,
    ];
}

function record_ai_runtime(?int $uid, string $route, bool $success, ?string $error = null, ?string $model = null, ?int $duration = null): void {
    try {
        $q = db()->prepare('INSERT INTO ai_runtime_events(user_id,route,model,duration_ms,success,error_message,created_at) VALUES(?,?,?,?,?,?,NOW())');
        $q->execute([$uid,$route,$model,$duration,$success?1:0,$error ? substr($error,0,500) : null]);
    } catch (Throwable $e) {}
}
