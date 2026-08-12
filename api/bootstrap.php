<?php
require_once __DIR__ . '/db.php';
$status = schema_status();
json_out($status, $status['ok'] ? 200 : 503);
