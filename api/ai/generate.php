<?php
require_once __DIR__ . '/common.php';
require_schema();
$uid = require_user_id();
$d = json_input();
$brief = trim($d['brief'] ?? '');
if (!$brief) json_out(['ok'=>false,'message'=>'Brief is required'],422);
assert_ai_quota($uid, 'generation');
$result = call_python_ai('/generate', ['user_id'=>$uid,'brief'=>$brief,'format'=>$d['format']??'Instagram portrait · 1080 × 1350']);
if (!$result['ok']) {
    $message = $result['data']['message'] ?? $result['error'] ?? 'Python AI service unavailable.';
    record_ai_runtime($uid,'generate',false,$message,null,$result['duration_ms']);
    json_out(['ok'=>false,'message'=>$message],502);
}
$data = $result['data'];
$pdo = db();
$q = $pdo->prepare('INSERT INTO ai_generations(user_id,project_id,prompt,response_json,status,created_at) VALUES(?,?,?,?,?,NOW())');
$q->execute([$uid,null,$brief,json_encode($data,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES),'completed']);
increment_ai_usage($uid,'generation');
record_ai_runtime($uid,'generate',true,null,$data['model']??null,$result['duration_ms']);
json_out($data);
