<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
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
     * Webhook endpoint for the Python AI service to trigger congestion alerts
     */
    public function webhookCongestionAlert(Request $request)
    {
        // Example payload: { "alert": "Traffic Congestion", "camera_id": "cam_01", "timestamp": "..." }
        $payload = $request->all();
        
        Log::warning('Traffic Congestion Alert received from Python AI service', $payload);

        // In a real application, we might broadcast this event to the frontend via WebSockets / Reverb
        // event(new \App\Events\CongestionAlertTriggered($payload));

        return response()->json(['status' => 'acknowledged']);
    }
}
