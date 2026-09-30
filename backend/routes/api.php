<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

use App\Http\Controllers\AuthController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\ParkingSessionController;
use App\Http\Controllers\RoiController;
use App\Http\Controllers\AiQueryController;
use App\Http\Controllers\ExitAlertController;

// ==============================================================================
// a. Sanctum-protected: Needs an admin token (Next.js dashboard).
// ==============================================================================
// (Note: Login and Register are public but belong to the dashboard auth flow)
Route::post('/register', [AuthController::class, 'register']);
Route::post('/login', [AuthController::class, 'login']);

Route::middleware('auth:sanctum')->group(function () {
    // Auth & Profile
    Route::post('/logout', [AuthController::class, 'logout']);
    Route::get('/user', function (Request $request) {
        return $request->user();
    });
    Route::put('/user/profile', [AuthController::class, 'updateProfile']);

    // Dashboard Metrics
    Route::get('/dashboard/metrics', [DashboardController::class, 'metrics']);
    Route::get('/dashboard/peak-hours', [DashboardController::class, 'peakHours']);
    Route::get('/dashboard/revenue-trends', [DashboardController::class, 'revenueTrends']);
    Route::get('/dashboard/demographics', [DashboardController::class, 'demographics']);
    Route::get('/dashboard/payment-insights', [DashboardController::class, 'paymentInsights']);

    // Parking Sessions
    Route::get('/parking-sessions/filter-options', [ParkingSessionController::class, 'filterOptions']);
    Route::get('/parking-sessions', [ParkingSessionController::class, 'index']);
    Route::get('/parking-sessions/{id}', [ParkingSessionController::class, 'show']);

    // ROI
    Route::post('/roi/coordinates', [RoiController::class, 'setCoordinates']);

    // Exit Alerts
    Route::get('/exit-alerts', [ExitAlertController::class, 'index']);
    Route::put('/exit-alerts/{id}/dismiss', [ExitAlertController::class, 'dismiss']);
    Route::put('/exit-alerts/{id}/override', [ExitAlertController::class, 'override']);
});

// ==============================================================================
// b. Public mobile: No login required (Mobile app).
// ==============================================================================
Route::get('/parking-sessions/plate/{license_plate}', [ParkingSessionController::class, 'findByPlate']);
Route::post('/parking-sessions/{id}/pay', [ParkingSessionController::class, 'pay']);
Route::post('/parking-sessions/{id}/pay-additional', [ParkingSessionController::class, 'payAdditional']);

// ==============================================================================
// c. Machine-to-machine: Trusted internal network only (Python services).
// ==============================================================================
Route::post('/webhooks/congestion', [RoiController::class, 'webhookCongestionAlert']);
Route::post('/ai/query', [AiQueryController::class, 'execute']);
Route::post('/parking-sessions/car-entry', [ParkingSessionController::class, 'carEntry']);
Route::post('/parking-sessions/car-exit', [ParkingSessionController::class, 'carExit']);
