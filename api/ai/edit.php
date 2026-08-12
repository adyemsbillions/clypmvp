<?php
require_once __DIR__ . '/common.php';
require_schema();
$uid = require_user_id();
$d = json_input();
$command = trim($d['command'] ?? '');
$design = $d['design'] ?? null;
$projectId = (int)($d['project_id'] ?? 0);
if (!$command || !is_array($design)) json_out(['ok'=>false,'message'=>'Command and design are required'],422);
assert_ai_quota($uid, 'edit');
$result = call_python_ai('/edit', ['user_id'=>$uid,'command'=>$command,'design'=>$design,'project_id'=>$projectId]);
if (!$result['ok']) {
    $message = $result['data']['message'] ?? $result['error'] ?? 'Python AI service unavailable.';
    record_ai_runtime($uid,'edit',false,$message,null,$result['duration_ms']);
    json_out(['ok'=>false,'message'=>$message],502);
}
$data = $result['data'];
$q = db()->prepare('INSERT INTO ai_edits(user_id,project_id,command,before_json,after_json,created_at) VALUES(?,?,?,?,?,NOW())');
$q->execute([$uid,$projectId?:null,$command,json_encode($design,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES),json_encode($data['design']??null,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)]);
increment_ai_usage($uid,'edit');
record_ai_runtime($uid,'edit',true,null,$data['model']??null,$result['duration_ms']);
json_out($data);
