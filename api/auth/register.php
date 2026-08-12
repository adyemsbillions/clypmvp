<?php
require_once __DIR__ . '/../db.php';
require_schema();
$data=json_input(); $name=trim($data['name']??''); $email=strtolower(trim($data['email']??'')); $password=$data['password']??'';
if(!$name||!filter_var($email,FILTER_VALIDATE_EMAIL)||strlen($password)<8) json_out(['ok'=>false,'message'=>'Enter a valid name, email and password (8+ characters).'],422);
try{$pdo=db();$q=$pdo->prepare('SELECT id FROM users WHERE email=?');$q->execute([$email]);if($q->fetch())json_out(['ok'=>false,'message'=>'An account already exists for this email.'],409);$q=$pdo->prepare('INSERT INTO users(name,email,password_hash,created_at,updated_at) VALUES(?,?,?,?,?)');$now=date('Y-m-d H:i:s');$q->execute([$name,$email,password_hash($password,PASSWORD_DEFAULT),$now,$now]);session_start();$_SESSION['user_id']=(int)$pdo->lastInsertId();json_out(['ok'=>true,'message'=>'Account created.','user'=>['id'=>$_SESSION['user_id'],'name'=>$name,'email'=>$email]],201);}catch(Throwable $e){json_out(['ok'=>false,'message'=>'Database not configured yet. Use the included schema and environment variables.'],503);}
