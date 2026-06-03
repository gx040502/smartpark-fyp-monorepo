<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

use App\Http\Controllers\AuthController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\ParkingSessionController;
use App\Http\Controllers\RoiController;
use App\Http\Controllers\AiQueryController;

// Public routes
Route::post('/register', [AuthController::class, 'register']);
Route::post('/login', [AuthController::class, 'login']);

// Python Webhook (would normally have its own auth/token, but public for mockup)
Route::post('/webhooks/congestion', [RoiController::class, 'webhookCongestionAlert']);

// AI Agent — SQL execution endpoint (called by the Python AI service)
Route::post('/ai/query', [AiQueryController::class, 'execute']);

// Protected routes
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

    // Parking Sessions
    Route::get('/parking-sessions', [ParkingSessionController::class, 'index']);
    Route::get('/parking-sessions/{id}', [ParkingSessionController::class, 'show']);

    // ROI
    Route::post('/roi/coordinates', [RoiController::class, 'setCoordinates']);
});
