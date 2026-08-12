<?php
require_once __DIR__ . '/../db.php';
require_schema();
$uid = require_user_id();
$pdo = db();
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $q=$pdo->prepare("SELECT id,name,format,updated_at,JSON_UNQUOTE(JSON_EXTRACT(current_design_json,'$.canvas.bg')) AS canvas_bg FROM projects WHERE user_id=? ORDER BY updated_at DESC");
    $q->execute([$uid]);
    json_out(['ok'=>true,'projects'=>$q->fetchAll()]);
}
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $d=json_input();$name=trim($d['name']??'Untitled design');$format=$d['format']??'1080 × 1350';$design=$d['design']??null;
    if(!is_array($design))json_out(['ok'=>false,'message'=>'Design payload required'],422);
    $now=date('Y-m-d H:i:s');
    $q=$pdo->prepare('INSERT INTO projects(user_id,name,format,current_design_json,created_at,updated_at) VALUES(?,?,?,?,?,?)');
    $q->execute([$uid,$name,$format,json_encode($design,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES),$now,$now]);
    $id=(int)$pdo->lastInsertId();
    $v=$pdo->prepare('INSERT INTO design_versions(project_id,version_number,design_json,created_at) VALUES(?,?,?,?)');
    $v->execute([$id,1,json_encode($design,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES),$now]);
    json_out(['ok'=>true,'project_id'=>$id,'version'=>1],201);
}
json_out(['ok'=>false,'message'=>'Method not allowed'],405);
