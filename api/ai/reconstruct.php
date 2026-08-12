<?php
require_once __DIR__ . '/common.php';
require_schema();
$uid = require_user_id();
$d = json_input();
$dataUrl = $d['data_url'] ?? '';
$filename = trim($d['filename'] ?? 'uploaded design');
if (!$dataUrl || !str_starts_with($dataUrl,'data:')) json_out(['ok'=>false,'message'=>'Uploaded file data is required'],422);
if (strlen($dataUrl) > 10 * 1024 * 1024) json_out(['ok'=>false,'message'=>'File is too large for this local MVP.'],413);
assert_ai_quota($uid, 'generation');
$result = call_python_ai('/reconstruct', ['user_id'=>$uid,'data_url'=>$dataUrl,'filename'=>$filename]);
if (!$result['ok']) {
    $message = $result['data']['message'] ?? $result['error'] ?? 'Python AI service unavailable.';
    record_ai_runtime($uid,'reconstruct',false,$message,null,$result['duration_ms']);
    json_out(['ok'=>false,'message'=>$message],502);
}
$data = $result['data'];
$q = db()->prepare('INSERT INTO ai_generations(user_id,project_id,prompt,response_json,status,created_at) VALUES(?,?,?,?,?,NOW())');
$q->execute([$uid,null,'Reconstruct uploaded design: '.$filename,json_encode($data,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES),'completed']);
increment_ai_usage($uid,'generation');
record_ai_runtime($uid,'reconstruct',true,null,$data['model']??null,$result['duration_ms']);
json_out($data);
