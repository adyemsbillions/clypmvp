<?php
require_once __DIR__ . '/../db.php';
require_schema();
$data=json_input();$email=strtolower(trim($data['email']??''));$password=$data['password']??'';if(!$email||!$password)json_out(['ok'=>false,'message'=>'Email and password are required.'],422);
try{$q=db()->prepare('SELECT id,name,email,password_hash FROM users WHERE email=?');$q->execute([$email]);$u=$q->fetch();if(!$u||!password_verify($password,$u['password_hash']))json_out(['ok'=>false,'message'=>'Incorrect email or password.'],401);session_start();session_regenerate_id(true);$_SESSION['user_id']=(int)$u['id'];unset($u['password_hash']);json_out(['ok'=>true,'message'=>'Welcome back.','user'=>$u]);}catch(Throwable $e){json_out(['ok'=>false,'message'=>'Database not configured yet.'],503);}
