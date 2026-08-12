<?php
require_once __DIR__ . '/../db.php';
require_schema();
$uid=require_user_id();$id=(int)($_GET['id']??0);if(!$id)json_out(['ok'=>false,'message'=>'Project id is required'],422);
$q=db()->prepare('SELECT id,name,format,current_design_json,created_at,updated_at FROM projects WHERE id=? AND user_id=?');
$q->execute([$id,$uid]);$p=$q->fetch();if(!$p)json_out(['ok'=>false,'message'=>'Project not found'],404);
$p['id']=(int)$p['id'];$p['design']=json_decode($p['current_design_json'],true);unset($p['current_design_json']);json_out(['ok'=>true,'project'=>$p]);
