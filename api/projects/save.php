<?php
require_once __DIR__ . '/../db.php';
require_schema();
$uid=require_user_id();$d=json_input();$id=(int)($d['id']??0);$design=$d['design']??null;
if(!$id||!is_array($design))json_out(['ok'=>false,'message'=>'Project id and design are required'],422);
$pdo=db();$pdo->beginTransaction();
try{
    $ownership=$pdo->prepare('SELECT id FROM projects WHERE id=? AND user_id=? FOR UPDATE');$ownership->execute([$id,$uid]);if(!$ownership->fetch())throw new RuntimeException('Project not found');
    $q=$pdo->prepare('SELECT COALESCE(MAX(version_number),0)+1 n FROM design_versions WHERE project_id=?');$q->execute([$id]);$n=(int)$q->fetch()['n'];$now=date('Y-m-d H:i:s');
    $u=$pdo->prepare('UPDATE projects SET name=?,format=?,current_design_json=?,updated_at=? WHERE id=? AND user_id=?');
    $u->execute([$d['name']??'Untitled design',$d['format']??'1080 × 1350',json_encode($design,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES),$now,$id,$uid]);
    $v=$pdo->prepare('INSERT INTO design_versions(project_id,version_number,design_json,created_at) VALUES(?,?,?,?)');$v->execute([$id,$n,json_encode($design,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES),$now]);
    $pdo->commit();json_out(['ok'=>true,'version'=>$n,'updated_at'=>$now]);
}catch(Throwable $e){if($pdo->inTransaction())$pdo->rollBack();json_out(['ok'=>false,'message'=>$e->getMessage()==='Project not found'?'Project not found':'Could not save project'],500);}
