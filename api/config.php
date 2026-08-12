<?php
require_once __DIR__ . '/env.php';
return [
  'app_env' => getenv('CLYP_ENV') ?: 'development',
  'app_url' => getenv('CLYP_APP_URL') ?: 'http://127.0.0.1:8080',
  'db' => [
    'host' => getenv('CLYP_DB_HOST') ?: '127.0.0.1',
    'port' => getenv('CLYP_DB_PORT') ?: '3306',
    'name' => getenv('CLYP_DB_NAME') ?: 'clyp',
    'user' => getenv('CLYP_DB_USER') ?: 'root',
    'pass' => getenv('CLYP_DB_PASS') !== false ? getenv('CLYP_DB_PASS') : '',
  ],
  'payment' => [
    'provider' => getenv('CLYP_PAYMENT_PROVIDER') ?: 'paystack',
    'secret_key' => getenv('CLYP_PAYSTACK_SECRET') ?: '',
    'public_key' => getenv('CLYP_PAYSTACK_PUBLIC') ?: '',
  ],
  'ai' => [
    'endpoint' => getenv('CLYP_AI_ENDPOINT') ?: 'http://127.0.0.1:8100',
    'internal_token' => getenv('CLYP_AI_INTERNAL_TOKEN') ?: 'change-me',
    'model' => getenv('CLYP_GEMINI_MODEL') ?: 'gemini-2.5-flash',
  ],
];
