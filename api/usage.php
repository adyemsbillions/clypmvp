<?php
require_once __DIR__ . '/db.php';
require_schema();
$uid=require_user_id();$pdo=db();$period=date('Y-m-01');
$q=$pdo->prepare('SELECT ai_generations_used,ai_edits_used FROM usage_monthly WHERE user_id=? AND period_start=?');$q->execute([$uid,$period]);$u=$q->fetch()?:['ai_generations_used'=>0,'ai_edits_used'=>0];
$user=$pdo->prepare('SELECT plan FROM users WHERE id=?');$user->execute([$uid]);$plan=$user->fetchColumn()?:'free';
$limits=match($plan){'pro'=>['designs'=>30,'edits'=>30],'single'=>['designs'=>1,'edits'=>0],default=>['designs'=>3,'edits'=>3]};
json_out(['ok'=>true,'plan'=>$plan,'designs'=>['used'=>(int)$u['ai_generations_used'],'limit'=>$limits['designs'],'remaining'=>max(0,$limits['designs']-(int)$u['ai_generations_used'])],'edits'=>['used'=>(int)$u['ai_edits_used'],'limit'=>$limits['edits'],'remaining'=>max(0,$limits['edits']-(int)$u['ai_edits_used'])]]);
