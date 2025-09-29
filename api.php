<?php
// API Proxy for Doc Scan AI
// Routes API calls to Python backend running on port 8000

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: https://docscan.adilabs.id');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Get request details
$request_uri = $_SERVER['REQUEST_URI'];
$method = $_SERVER['REQUEST_METHOD'];
$input = file_get_contents('php://input');

// Remove /api.php from the URI to get the actual API path
$api_path = str_replace('/api.php', '', $request_uri);

// Route to Python backend (adjust URL as needed)
$backend_url = 'http://localhost:8000' . $api_path;

// Initialize cURL
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $backend_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
curl_setopt($ch, CURLOPT_TIMEOUT, 300); // 5 minutes timeout for OCR processing

// Handle POST data
if ($input && in_array($method, ['POST', 'PUT', 'PATCH'])) {
    curl_setopt($ch, CURLOPT_POSTFIELDS, $input);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Content-Length: ' . strlen($input)
    ]);
}

// Handle file uploads
if (isset($_FILES) && !empty($_FILES)) {
    $files = [];
    foreach ($_FILES as $key => $file) {
        if ($file['error'] === UPLOAD_ERR_OK) {
            $files[$key] = new CURLFile($file['tmp_name'], $file['type'], $file['name']);
        }
    }
    if (!empty($files)) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $files);
        curl_setopt($ch, CURLOPT_HTTPHEADER, []); // Let cURL set multipart headers
    }
}

// Execute request
$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

// Handle errors
if ($response === false || !empty($error)) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Backend connection failed',
        'message' => $error ?: 'Could not connect to Python backend',
        'backend_url' => $backend_url
    ]);
    exit;
}

// Return response
http_response_code($http_code);
echo $response;
?>