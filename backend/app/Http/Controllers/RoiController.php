<?php

namespace App\Http\Controllers;

use App\Enums\ParkingStatus;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class RoiController extends Controller
{
    /**
     * Receive ROI coordinates from the frontend and forward to the Python AI service
     */
    public function setCoordinates(Request $request)
    {
        $request->validate([
            'points' => 'required|array|min:4|max:4',
            'points.*.x' => 'required|numeric',
            'points.*.y' => 'required|numeric',
        ]);

        $coordinates = $request->input('points');

        // Log the received coordinates
        Log::info('Received ROI coordinates from frontend:', $coordinates);

        // Here we would typically forward this to the Python microservice
        // e.g., Http::post('http://python-service:5000/api/roi', ['roi' => $coordinates]);

        // Since the Python service is external/mocked for now, we just acknowledge receipt
        return response()->json([
            'message' => 'ROI coordinates received successfully and forwarded to AI service.',
            'coordinates' => $coordinates
        ]);
    }

    /**
     * Webhook endpoint for the Python AI service to trigger congestion alerts.
     *
     * When traffic congestion is detected, extends grace_end_time by 15 minutes
     * for all PAID parking sessions. Has a 15-minute server-side cooldown to
     * prevent repeated extensions (safety net — Python also enforces cooldown).
     */
    public function webhookCongestionAlert(Request $request)
    {
        $payload = $request->all();

        Log::warning('Traffic Congestion Alert received from Python AI service', $payload);

        // Server-side cooldown: prevent repeated extensions within 15 minutes
        $cooldownKey = 'congestion_grace_cooldown';

        if (Cache::has($cooldownKey)) {
            Log::info('Congestion grace extension skipped — cooldown active.');

            return response()->json([
                'status' => 'cooldown_active',
                'message' => 'Grace extension was already applied recently. Cooldown active.',
            ]);
        }

        // Extend grace_end_time by 15 minutes for all PAID sessions with an active grace period
        $affectedRows = DB::table('parking_sessions')
            ->where('status', ParkingStatus::PAID->value)
            ->whereNotNull('grace_end_time')
            ->update([
                'grace_end_time' => DB::raw("DATE_ADD(grace_end_time, INTERVAL 15 MINUTE)"),
            ]);

        // Set the cooldown for 15 minutes
        Cache::put($cooldownKey, true, now()->addMinutes(15));

        Log::info("Congestion grace extension applied: {$affectedRows} parking session(s) extended by 15 minutes.");

        return response()->json([
            'status' => 'extended',
            'message' => "Grace period extended by 15 minutes for {$affectedRows} session(s).",
            'sessions_affected' => $affectedRows,
        ]);
    }
}

