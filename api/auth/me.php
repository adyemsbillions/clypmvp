<?php
require_once __DIR__ . '/../db.php';
require_schema();$id=session_user_id();if(!$id)json_out(['ok'=>false,'message'=>'Unauthenticated'],401);try{$q=db()->prepare('SELECT id,name,email,plan,created_at FROM users WHERE id=?');$q->execute([$id]);json_out(['ok'=>true,'user'=>$q->fetch()]);}catch(Throwable $e){json_out(['ok'=>false,'message'=>'Database unavailable'],503);}
